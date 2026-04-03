from __future__ import annotations

import json
import logging
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from config.config import Config


logger = logging.getLogger(__name__)


class VectorStore:
    _schema_ready = False
    _schema_lock = threading.Lock()

    def __init__(self):
        self.enabled = all(
            [
                Config.POSTGRES_HOST,
                Config.POSTGRES_DB,
                Config.POSTGRES_USER,
                Config.POSTGRES_PASSWORD,
            ]
        )
        self.embedding_dimensions = max(1, int(getattr(Config, "BEDROCK_EMBEDDING_DIMENSIONS", 1024) or 1024))

    @contextmanager
    def _connect(self) -> Iterator[psycopg.Connection]:
        if not self.enabled:
            raise RuntimeError("Postgres vector store is not configured.")
        connection = psycopg.connect(
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            dbname=Config.POSTGRES_DB,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            row_factory=dict_row,
            autocommit=True,
        )
        try:
            self._ensure_schema_ready(connection)
            register_vector(connection)
            yield connection
        finally:
            connection.close()

    def _ensure_schema_ready(self, connection: psycopg.Connection) -> None:
        if not self.enabled or self.__class__._schema_ready:
            return

        with self.__class__._schema_lock:
            if self.__class__._schema_ready:
                return

            connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
            connection.execute("CREATE SCHEMA IF NOT EXISTS rag")
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS rag.conversation_embeddings (
                    id uuid PRIMARY KEY,
                    user_id uuid NOT NULL,
                    patient_id uuid NULL,
                    conversation_id uuid NOT NULL,
                    source_turn_id text NULL,
                    embedding_model text NOT NULL,
                    embedding vector({self.embedding_dimensions}) NOT NULL,
                    embedding_text text NOT NULL,
                    facts_summary jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                    signal_score numeric(4,3) NOT NULL,
                    triage_level varchar(20) NULL,
                    clinical_topic varchar(100) NULL,
                    created_at timestamptz NOT NULL DEFAULT NOW(),
                    episode_timestamp timestamptz NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversation_embeddings_user_conversation_created
                    ON rag.conversation_embeddings (user_id, conversation_id, created_at DESC)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversation_embeddings_user_signal
                    ON rag.conversation_embeddings (user_id, signal_score)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversation_embeddings_triage
                    ON rag.conversation_embeddings (triage_level)
                """
            )
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS rag.user_summary_embeddings (
                    id uuid PRIMARY KEY,
                    user_id uuid NOT NULL UNIQUE,
                    patient_id uuid NOT NULL UNIQUE,
                    clinical_summary_id uuid NOT NULL,
                    embedding_model text NOT NULL,
                    embedding vector({self.embedding_dimensions}) NOT NULL,
                    summary_text text NOT NULL,
                    clinical_snapshot jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                    summary_version integer NOT NULL,
                    source_updated_at timestamptz NULL,
                    created_at timestamptz NOT NULL DEFAULT NOW(),
                    updated_at timestamptz NOT NULL DEFAULT NOW()
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_summary_embeddings_summary_version
                    ON rag.user_summary_embeddings (summary_version)
                """
            )
            self.__class__._schema_ready = True

    @staticmethod
    def _json_default(value: Any):
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _serialize_json(payload: dict[str, Any] | None) -> str:
        return json.dumps(payload or {}, ensure_ascii=False, default=VectorStore._json_default)

    def insert_conversation_embedding(
        self,
        *,
        user_id: str,
        patient_id: str | None,
        conversation_id: str,
        source_turn_id: str | None,
        embedding_model: str,
        embedding: list[float],
        embedding_text: str,
        facts_summary: dict[str, Any],
        signal_score: float,
        triage_level: str | None,
        clinical_topic: str | None,
        episode_timestamp: datetime | None = None,
    ) -> None:
        if not self.enabled or not embedding:
            return
        query = """
            INSERT INTO rag.conversation_embeddings (
                id,
                user_id,
                patient_id,
                conversation_id,
                source_turn_id,
                embedding_model,
                embedding,
                embedding_text,
                facts_summary,
                signal_score,
                triage_level,
                clinical_topic,
                created_at,
                episode_timestamp
            )
            VALUES (
                %(id)s,
                %(user_id)s::uuid,
                %(patient_id)s::uuid,
                %(conversation_id)s::uuid,
                %(source_turn_id)s,
                %(embedding_model)s,
                %(embedding)s,
                %(embedding_text)s,
                %(facts_summary)s::jsonb,
                %(signal_score)s,
                %(triage_level)s,
                %(clinical_topic)s,
                %(created_at)s,
                %(episode_timestamp)s
            )
        """
        params = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "patient_id": patient_id,
            "conversation_id": conversation_id,
            "source_turn_id": source_turn_id,
            "embedding_model": embedding_model,
            "embedding": embedding,
            "embedding_text": embedding_text,
            "facts_summary": self._serialize_json(facts_summary),
            "signal_score": signal_score,
            "triage_level": triage_level,
            "clinical_topic": clinical_topic,
            "created_at": datetime.utcnow(),
            "episode_timestamp": episode_timestamp,
        }
        try:
            with self._connect() as connection:
                connection.execute(query, params)
        except Exception as exc:
            logger.warning("Could not insert conversation embedding: %s", exc)

    def search_conversation_embeddings(
        self,
        *,
        user_id: str,
        conversation_id: str,
        query_embedding: list[float],
        limit: int = 5,
        min_signal_score: float = 0.25,
    ) -> list[dict[str, Any]]:
        if not self.enabled or not query_embedding:
            return []
        query = """
            SELECT
                source_turn_id,
                embedding_text AS text,
                facts_summary,
                triage_level,
                signal_score,
                created_at,
                1 - (embedding <=> %(embedding)s) AS score
            FROM rag.conversation_embeddings
            WHERE user_id = %(user_id)s::uuid
              AND conversation_id = %(conversation_id)s::uuid
              AND signal_score >= %(min_signal_score)s
            ORDER BY embedding <=> %(embedding)s
            LIMIT %(limit)s
        """
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    query,
                    {
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "embedding": query_embedding,
                        "min_signal_score": min_signal_score,
                        "limit": limit,
                    },
                ).fetchall()
        except Exception as exc:
            logger.warning("Could not search conversation embeddings: %s", exc)
            return []
        return [self._normalize_search_row(row) for row in rows]

    def search_global_conversation_embeddings(
        self,
        *,
        user_id: str,
        query_embedding: list[float],
        current_conversation_id: str | None = None,
        limit: int = 2,
        min_signal_score: float = 0.25,
    ) -> list[dict[str, Any]]:
        if not self.enabled or not query_embedding:
            return []
        exclusion_clause = ""
        params: dict[str, Any] = {
            "user_id": user_id,
            "embedding": query_embedding,
            "min_signal_score": min_signal_score,
            "limit": limit,
        }
        if current_conversation_id:
            exclusion_clause = "AND conversation_id <> %(conversation_id)s::uuid"
            params["conversation_id"] = current_conversation_id
        query = f"""
            SELECT
                conversation_id,
                source_turn_id,
                embedding_text AS text,
                facts_summary,
                triage_level,
                signal_score,
                created_at,
                1 - (embedding <=> %(embedding)s) AS score
            FROM rag.conversation_embeddings
            WHERE user_id = %(user_id)s::uuid
              AND signal_score >= %(min_signal_score)s
              {exclusion_clause}
            ORDER BY embedding <=> %(embedding)s
            LIMIT %(limit)s
        """
        try:
            with self._connect() as connection:
                rows = connection.execute(query, params).fetchall()
        except Exception as exc:
            logger.warning("Could not search global conversation embeddings: %s", exc)
            return []
        return [self._normalize_search_row(row) for row in rows]

    def upsert_user_summary_embedding(
        self,
        *,
        user_id: str,
        patient_id: str,
        clinical_summary_id: str,
        embedding_model: str,
        embedding: list[float],
        summary_text: str,
        clinical_snapshot: dict[str, Any],
        summary_version: int,
        source_updated_at: datetime | None,
    ) -> None:
        if not self.enabled or not embedding:
            return
        query = """
            INSERT INTO rag.user_summary_embeddings (
                id,
                user_id,
                patient_id,
                clinical_summary_id,
                embedding_model,
                embedding,
                summary_text,
                clinical_snapshot,
                summary_version,
                source_updated_at,
                created_at,
                updated_at
            )
            VALUES (
                %(id)s,
                %(user_id)s::uuid,
                %(patient_id)s::uuid,
                %(clinical_summary_id)s::uuid,
                %(embedding_model)s,
                %(embedding)s,
                %(summary_text)s,
                %(clinical_snapshot)s::jsonb,
                %(summary_version)s,
                %(source_updated_at)s,
                %(created_at)s,
                %(updated_at)s
            )
            ON CONFLICT (user_id) DO UPDATE SET
                patient_id = EXCLUDED.patient_id,
                clinical_summary_id = EXCLUDED.clinical_summary_id,
                embedding_model = EXCLUDED.embedding_model,
                embedding = EXCLUDED.embedding,
                summary_text = EXCLUDED.summary_text,
                clinical_snapshot = EXCLUDED.clinical_snapshot,
                summary_version = EXCLUDED.summary_version,
                source_updated_at = EXCLUDED.source_updated_at,
                updated_at = EXCLUDED.updated_at
        """
        now = datetime.utcnow()
        params = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "patient_id": patient_id,
            "clinical_summary_id": clinical_summary_id,
            "embedding_model": embedding_model,
            "embedding": embedding,
            "summary_text": summary_text,
            "clinical_snapshot": self._serialize_json(clinical_snapshot),
            "summary_version": summary_version,
            "source_updated_at": source_updated_at,
            "created_at": now,
            "updated_at": now,
        }
        try:
            with self._connect() as connection:
                connection.execute(query, params)
        except Exception as exc:
            logger.warning("Could not upsert user summary embedding: %s", exc)

    def get_user_summary_context(self, *, user_id: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        query = """
            SELECT
                clinical_summary_id,
                summary_text,
                clinical_snapshot,
                summary_version,
                source_updated_at,
                updated_at
            FROM rag.user_summary_embeddings
            WHERE user_id = %(user_id)s::uuid
            LIMIT 1
        """
        try:
            with self._connect() as connection:
                row = connection.execute(query, {"user_id": user_id}).fetchone()
        except Exception as exc:
            logger.warning("Could not fetch user summary embedding: %s", exc)
            return None
        if not row:
            return None
        return {
            "clinical_summary_id": str(row.get("clinical_summary_id")) if row.get("clinical_summary_id") else None,
            "summary_text": row.get("summary_text", ""),
            "clinical_snapshot": row.get("clinical_snapshot", {}) or {},
            "summary_version": row.get("summary_version"),
            "source_updated_at": self._as_iso(row.get("source_updated_at")),
            "updated_at": self._as_iso(row.get("updated_at")),
        }

    @staticmethod
    def _as_iso(value: Any) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        if value is None:
            return None
        return str(value)

    def _normalize_search_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "score": float(row.get("score", 0.0) or 0.0),
            "text": row.get("text", ""),
            "source_turn_id": row.get("source_turn_id"),
            "conversation_id": str(row.get("conversation_id")) if row.get("conversation_id") else None,
            "triage_level": row.get("triage_level"),
            "signal_score": float(row.get("signal_score", 0.0) or 0.0),
            "facts_summary": row.get("facts_summary", {}) or {},
            "metadata": {
                "created_at": self._as_iso(row.get("created_at")),
                "triage_level": row.get("triage_level"),
            },
        }
