from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from config.config import Config
from models.conversation import ConversationalDatasetManager
from services.embeddings import build_embedding_payload, generate_embedding
from services.input_validate import MessageAnalysis
from services.medical_facts import FactsSummary, MedicalFact

try:
    from data.connect import context_redis_client, mongo_db
except Exception:  # pragma: no cover
    context_redis_client = None
    mongo_db = None


logger = logging.getLogger(__name__)


class ConversationContextService:
    KEY_CTX = "chat:ctx:{user_id}:{conversation_id}"
    KEY_SUMMARY = "chat:idx:summary:{user_id}:{conversation_id}"
    KEY_LOOP = "chat:idx:loop:{user_id}:{conversation_id}"

    def __init__(self):
        self.context_ttl = Config.CHAT_CONTEXT_TTL_SECONDS
        self.window_n = Config.CHAT_CONTEXT_WINDOW_N
        self.top_k = Config.CHAT_CONTEXT_TOP_K
        self.embedding_collection = mongo_db["conversation_embeddings"] if mongo_db is not None else None
        self.conversation_collection = mongo_db["conversations"] if mongo_db is not None else None
        try:
            if self.embedding_collection is not None:
                self.embedding_collection.create_index([("user_id", 1), ("conversation_id", 1), ("timestamp", -1)])
                self.embedding_collection.create_index([("user_id", 1), ("conversation_id", 1), ("source_turn_id", 1)])
        except Exception as exc:
            logger.warning("Could not ensure embedding indexes: %s", exc)

    def _ctx_key(self, user_id: str, conversation_id: str) -> str:
        return self.KEY_CTX.format(user_id=user_id, conversation_id=conversation_id)

    def _summary_key(self, user_id: str, conversation_id: str) -> str:
        return self.KEY_SUMMARY.format(user_id=user_id, conversation_id=conversation_id)

    def _loop_key(self, user_id: str, conversation_id: str) -> str:
        return self.KEY_LOOP.format(user_id=user_id, conversation_id=conversation_id)

    @staticmethod
    def _redis_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8")
        if isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        limit = min(len(a), len(b))
        if limit == 0:
            return 0.0
        lhs = [float(value) for value in a[:limit]]
        rhs = [float(value) for value in b[:limit]]
        dot = sum(x * y for x, y in zip(lhs, rhs))
        norm_lhs = sum(x * x for x in lhs) ** 0.5
        norm_rhs = sum(y * y for y in rhs) ** 0.5
        denom = norm_lhs * norm_rhs
        if denom == 0.0:
            return 0.0
        return float(dot / denom)

    @staticmethod
    def _compact_summary_text(facts_summary: FactsSummary) -> str:
        fragments = []
        if facts_summary.chief_complaints:
            fragments.append("motivo: " + ", ".join(facts_summary.chief_complaints[:2]))
        if facts_summary.symptoms:
            fragments.append("sintomas: " + ", ".join(facts_summary.symptoms[:3]))
        if facts_summary.duration:
            fragments.append("duracion: " + facts_summary.duration)
        if facts_summary.pain_scale is not None:
            fragments.append(f"dolor: {facts_summary.pain_scale}/10")
        if facts_summary.red_flags:
            fragments.append("red_flags: " + ", ".join(facts_summary.red_flags[:2]))
        if facts_summary.history:
            fragments.append("antecedentes: " + ", ".join(facts_summary.history[:2]))
        return " | ".join(fragments)

    def append_turn(
        self,
        user_id: str,
        conversation_id: str,
        user_msg: str,
        bot_msg: str,
        metadata: dict[str, Any],
        *,
        facts: list[MedicalFact] | None = None,
        facts_summary: FactsSummary | None = None,
        analysis: MessageAnalysis | None = None,
    ):
        key = self._ctx_key(user_id, conversation_id)
        facts_summary = facts_summary or FactsSummary()
        analysis = analysis or MessageAnalysis(is_valid=True, analysis_type="clinical", clinical_signal_score=0.0)
        embedding_payload = build_embedding_payload(user_msg, facts or [], analysis, facts_summary)
        turn = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": user_msg,
            "assistant_message": bot_msg,
            "metadata": metadata or {},
            "facts_summary": facts_summary.model_dump(),
            "signal_score": analysis.clinical_signal_score,
            "embedding_text": embedding_payload.embedding_text,
            "triage_level": (metadata or {}).get("triage_level"),
        }
        try:
            if context_redis_client is not None:
                context_redis_client.rpush(key, json.dumps(turn, ensure_ascii=False))
                context_redis_client.expire(key, self.context_ttl)
                context_redis_client.ltrim(key, -self.window_n, -1)
        except Exception as exc:
            logger.warning("Could not persist turn to Redis: %s", exc)

        summary_key = self._summary_key(user_id, conversation_id)
        summary_text = self._compact_summary_text(facts_summary)
        try:
            if context_redis_client is not None:
                context_redis_client.set(summary_key, summary_text, ex=self.context_ttl)
        except Exception as exc:
            logger.warning("Could not update summary cache: %s", exc)

        if embedding_payload.skipped:
            return

        try:
            embedding = generate_embedding(embedding_payload.embedding_text)
            if self.embedding_collection is not None:
                self.embedding_collection.insert_one(
                    {
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "source_turn_id": (metadata or {}).get("source_turn_id"),
                        "text": embedding_payload.embedding_text,
                        "embedding": embedding,
                        "timestamp": datetime.utcnow(),
                        "metadata": metadata or {},
                        "facts_summary": facts_summary.model_dump(),
                        "signal_score": analysis.clinical_signal_score,
                    }
                )
        except Exception as exc:
            logger.warning("Error generating/storing embeddings: %s", exc)

    def get_recent_window(self, user_id: str, conversation_id: str, n: int | None = None) -> list[dict[str, Any]]:
        key = self._ctx_key(user_id, conversation_id)
        n = n or self.window_n
        if context_redis_client is None:
            return []
        try:
            turns = context_redis_client.lrange(key, -n, -1)
        except Exception:
            return []
        results = []
        for item in turns:
            try:
                results.append(json.loads(item))
            except Exception:
                continue
        return results

    def get_semantic_context(self, user_id: str, conversation_id: str, query_text: str, k: int | None = None) -> list[dict[str, Any]]:
        if self.embedding_collection is None:
            return []
        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return []
        k = k or self.top_k
        docs = list(
            self.embedding_collection.find(
                {"user_id": user_id, "conversation_id": conversation_id, "signal_score": {"$gte": 0.25}},
                {"text": 1, "embedding": 1, "metadata": 1, "source_turn_id": 1, "timestamp": 1, "facts_summary": 1},
            ).sort("timestamp", -1).limit(100)
        )
        scored = []
        for doc in docs:
            score = self._cosine(query_embedding, doc.get("embedding", []))
            if score > 0:
                scored.append(
                    {
                        "score": score,
                        "text": doc.get("text", ""),
                        "metadata": doc.get("metadata", {}),
                        "source_turn_id": doc.get("source_turn_id"),
                        "facts_summary": doc.get("facts_summary", {}),
                    }
                )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:k]

    def get_global_semantic_context(self, user_id: str, query_text: str, current_conversation_id: str | None = None, k: int | None = None) -> list[dict[str, Any]]:
        if self.embedding_collection is None:
            return []
        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return []
        query = {"user_id": user_id, "signal_score": {"$gte": 0.25}}
        if current_conversation_id:
            query["conversation_id"] = {"$ne": current_conversation_id}
        docs = list(
            self.embedding_collection.find(
                query,
                {"text": 1, "embedding": 1, "metadata": 1, "source_turn_id": 1, "timestamp": 1, "conversation_id": 1, "facts_summary": 1},
            ).sort("timestamp", -1).limit(200)
        )
        scored = []
        for doc in docs:
            score = self._cosine(query_embedding, doc.get("embedding", []))
            if score > 0:
                scored.append(
                    {
                        "score": score,
                        "text": doc.get("text", ""),
                        "metadata": doc.get("metadata", {}),
                        "source_turn_id": doc.get("source_turn_id"),
                        "conversation_id": doc.get("conversation_id"),
                        "facts_summary": doc.get("facts_summary", {}),
                    }
                )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:k or self.top_k]

    def get_global_patient_context_mongo(self, user_id: str, current_conversation_id: str | None = None, max_conversations: int = 5) -> dict[str, Any]:
        if self.conversation_collection is None:
            return {"recent_conversations": []}
        query = {
            "user_id": user_id,
            "$or": [{"lifecycle_status": {"$exists": False}}, {"lifecycle_status": {"$ne": "deleted"}}],
        }
        if current_conversation_id:
            query["_id"] = {"$ne": current_conversation_id}
        conversations = list(
            self.conversation_collection.find(
                query,
                {"_id": 1, "triaje_level": 1, "timestamp": 1, "medical_context": 1},
            ).sort("timestamp", -1).limit(max_conversations)
        )
        dataset_manager = ConversationalDatasetManager()
        compact = []
        for conv in conversations:
            conv = dataset_manager._serialize_conversation_record(conv)
            medical_context = conv.get("medical_context", {})
            facts_summary = medical_context.get("facts_summary", {}) if isinstance(medical_context, dict) else {}
            compact.append(
                {
                    "conversation_id": str(conv.get("_id")),
                    "triaje_level": conv.get("triaje_level"),
                    "timestamp": str(conv.get("timestamp")),
                    "facts_summary": facts_summary,
                }
            )
        return {"recent_conversations": compact}

    def detect_loop(self, user_id: str, conversation_id: str, assistant_message: str) -> bool:
        key = self._loop_key(user_id, conversation_id)
        current = {"last": assistant_message, "count": 1}
        if context_redis_client is None:
            return False
        try:
            previous = context_redis_client.get(key)
            if previous:
                payload = json.loads(self._redis_text(previous))
                if payload.get("last", "").strip().lower() == assistant_message.strip().lower():
                    current["count"] = int(payload.get("count", 1)) + 1
            context_redis_client.set(key, json.dumps(current), ex=self.context_ttl)
        except Exception:
            return False
        return current["count"] >= 2

    def get_summary(self, user_id: str, conversation_id: str) -> str:
        if context_redis_client is None:
            return ""
        try:
            raw = context_redis_client.get(self._summary_key(user_id, conversation_id))
        except Exception:
            return ""
        return self._redis_text(raw)

    def build_retrieval_context(self, user_id: str, conversation_id: str, current_facts_summary: FactsSummary) -> dict[str, Any]:
        query_text = self._compact_summary_text(current_facts_summary)
        return {
            "conversation_summary": self.get_summary(user_id, conversation_id),
            "semantic_context": self.get_semantic_context(user_id, conversation_id, query_text, self.top_k),
            "global_semantic_context": self.get_global_semantic_context(user_id, query_text, current_conversation_id=conversation_id, k=min(2, self.top_k)),
            "global_mongo_context": self.get_global_patient_context_mongo(user_id, current_conversation_id=conversation_id),
        }

    def build_prompt_context(
        self,
        *,
        user_id: str,
        conversation_id: str,
        user_input: str,
        current_context: dict[str, Any],
        missing_questions: list[str],
        questions_selected: list[str],
        postgres_context: dict[str, Any] | None = None,
        triage_level: str | None,
        facts_summary: FactsSummary | None = None,
    ) -> dict[str, Any]:
        retrieval = self.build_retrieval_context(user_id, conversation_id, facts_summary or FactsSummary())
        recent_turns = self.get_recent_window(user_id, conversation_id, 2)
        return {
            **(current_context or {}),
            "user_input": user_input,
            "conversation_summary": retrieval.get("conversation_summary", ""),
            "recent_turns": recent_turns[-2:],
            "semantic_context": retrieval.get("semantic_context", []),
            "global_semantic_context": retrieval.get("global_semantic_context", []),
            "global_mongo_context": retrieval.get("global_mongo_context", {}),
            "postgres_context": postgres_context or {},
            "missing_questions": (missing_questions or [])[:2],
            "questions_selected": (questions_selected or [])[:2],
            "triage_level": triage_level,
            "facts_summary": (facts_summary or FactsSummary()).model_dump(),
        }
