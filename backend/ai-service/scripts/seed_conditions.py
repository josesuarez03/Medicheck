"""Carga el catalogo de condiciones (scripts/data/conditions.yaml) en pgvector.

Genera embeddings via Bedrock (con fallback deterministico hash-based de
services.embeddings si Bedrock no esta disponible) y hace upsert por
condition_id en rag.conditions_catalog.

Uso:
    python scripts/seed_conditions.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Permitir ejecutar el script desde cualquier cwd: anadir la raiz de ai-service
# (carpeta padre de scripts/) al sys.path.
_AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(_AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_ROOT))

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML es necesario para seed_conditions.py") from exc

from config.config import Config
from services.embeddings import generate_embedding
from services.vector_store import VectorStore


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_conditions")

_DATA_FILE = _AI_SERVICE_ROOT / "scripts" / "data" / "conditions.yaml"


def _build_embedding_text(condition: dict) -> str:
    """Texto estructurado que se embebe: nombre + sinonimos + senales.

    Asi la busqueda semantica casa tanto con terminologia clinica como con la
    forma coloquial en que la gente describe su situacion.
    """
    parts = [str(condition.get("name", ""))]
    synonyms = condition.get("synonyms") or []
    signals = condition.get("signals") or []
    if synonyms:
        parts.append("tambien descrito como: " + ", ".join(synonyms))
    if signals:
        parts.append("senales: " + ", ".join(signals))
    return " | ".join(p for p in parts if p.strip())


def load_conditions() -> list[dict]:
    if not _DATA_FILE.exists():
        raise SystemExit(f"No se encontro el catalogo: {_DATA_FILE}")
    payload = yaml.safe_load(_DATA_FILE.read_text(encoding="utf-8")) or {}
    conditions = payload.get("conditions", [])
    if not isinstance(conditions, list):
        raise SystemExit("conditions.yaml debe tener una lista 'conditions'.")
    return conditions


def seed() -> int:
    store = VectorStore()
    if not store.enabled:
        raise SystemExit(
            "Vector store deshabilitado: faltan variables de Postgres "
            "(POSTGRES_HOST/DB/USER/PASSWORD)."
        )

    conditions = load_conditions()
    embedding_model = Config.BEDROCK_EMBEDDING_MODEL_ID or "deterministic_fallback"
    inserted = 0
    failed = 0
    for condition in conditions:
        condition_id = str(condition.get("condition_id") or "").strip()
        if not condition_id:
            logger.warning("Condicion sin condition_id, omitida: %s", condition.get("name"))
            failed += 1
            continue
        embedding_text = _build_embedding_text(condition)
        embedding = generate_embedding(embedding_text)
        ok = store.upsert_condition(
            condition_id=condition_id,
            name=str(condition.get("name", condition_id)),
            category=str(condition.get("category", "physical")),
            synonyms=list(condition.get("synonyms") or []),
            signals=list(condition.get("signals") or []),
            urgency_level=str(condition.get("urgency_level", "moderate")),
            next_step=str(condition.get("next_step", "doctor")),
            country_context=str(condition.get("country_context", "ALL")),
            description=condition.get("description"),
            source=condition.get("source"),
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_text=embedding_text,
        )
        if ok:
            inserted += 1
        else:
            failed += 1
            logger.warning("No se pudo cargar la condicion: %s", condition_id)

    logger.info("Catalogo cargado: %s condiciones (fallidas: %s)", inserted, failed)
    return inserted


if __name__ == "__main__":
    count = seed()
    print(f"OK: {count} condiciones cargadas en rag.conditions_catalog")
