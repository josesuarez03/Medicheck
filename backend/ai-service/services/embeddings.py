from __future__ import annotations

import hashlib
import json
import logging
from typing import Literal

from pydantic import BaseModel, Field

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None

from config.config import Config
from services.input_validate import MessageAnalysis
from services.medical_facts import FactsSummary, MedicalFact, build_facts_summary


logger = logging.getLogger(__name__)
_FALLBACK_DIMENSION = 16


class EmbeddingPayload(BaseModel):
    skipped: bool
    reason: str | None = None
    signal_score: float
    embedding_target: Literal["clinical_hybrid"] = "clinical_hybrid"
    embedding_text: str = ""
    facts_used: list[str] = Field(default_factory=list)


def _hash_embedding(text: str, dimension: int = _FALLBACK_DIMENSION) -> list[float]:
    digest = hashlib.sha256((text or "").encode("utf-8")).digest()
    raw = [digest[i % len(digest)] for i in range(dimension)]
    return [round((value / 255.0) * 2 - 1, 6) for value in raw]


def should_embed(signal_score: float, facts: list[MedicalFact]) -> bool:
    has_clinical_fact = any(
        fact.clinical_role in {"chief_complaint", "duration", "pain_scale", "red_flag"}
        or fact.category in {"SYMPTOM", "MEDICATION", "ALLERGY", "MEDICAL_HISTORY"}
        for fact in facts
        if not fact.negated
    )
    if has_clinical_fact:
        return True
    return signal_score >= 0.25


def _ordered_fields(summary: FactsSummary) -> list[tuple[str, str]]:
    return [
        ("motivo_consulta", ", ".join(summary.chief_complaints)),
        ("sintomas", ", ".join(summary.symptoms)),
        ("duracion", summary.duration or ""),
        ("intensidad", f"{summary.pain_scale}/10" if summary.pain_scale is not None else ""),
        ("localizacion", ", ".join(summary.body_sites)),
        ("red_flags", ", ".join(summary.red_flags)),
        ("medicacion", ", ".join(summary.medications)),
        ("alergias", ", ".join(summary.allergies)),
        ("antecedentes", ", ".join(summary.history)),
        ("impacto_funcional", ", ".join(summary.functional_impact)),
    ]


def build_embedding_payload(
    text: str,
    facts: list[MedicalFact],
    analysis: MessageAnalysis,
    facts_summary: FactsSummary | None = None,
) -> EmbeddingPayload:
    facts_summary = facts_summary or build_facts_summary(facts)
    if not should_embed(analysis.clinical_signal_score, facts):
        return EmbeddingPayload(
            skipped=True,
            reason="low_clinical_signal",
            signal_score=analysis.clinical_signal_score,
            embedding_text="",
            facts_used=[],
        )

    ordered_fields = [(label, value) for label, value in _ordered_fields(facts_summary) if value]
    embedding_text = " | ".join(f"{label}: {value}" for label, value in ordered_fields)
    facts_used = [fact.fact_id for fact in facts if not fact.negated][:12]

    if not embedding_text.strip():
        return EmbeddingPayload(
            skipped=True,
            reason="empty_clinical_payload",
            signal_score=analysis.clinical_signal_score,
            embedding_text="",
            facts_used=facts_used,
        )

    return EmbeddingPayload(
        skipped=False,
        signal_score=analysis.clinical_signal_score,
        embedding_text=embedding_text,
        facts_used=facts_used,
    )


def generate_embedding(payload_text: str) -> list[float]:
    if not payload_text:
        return []
    if boto3 is None or not Config.BEDROCK_EMBEDDING_MODEL_ID or not Config.AWS_REGION:
        return _hash_embedding(payload_text)
    try:
        client = boto3.client("bedrock-runtime", region_name=Config.AWS_REGION)
        response = client.invoke_model(
            modelId=Config.BEDROCK_EMBEDDING_MODEL_ID,
            body=json.dumps({"inputText": payload_text}),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        embedding = payload.get("embedding", [])
        return embedding if isinstance(embedding, list) else _hash_embedding(payload_text)
    except Exception as exc:
        logger.warning("Falling back to deterministic embedding: %s", exc)
        return _hash_embedding(payload_text)
