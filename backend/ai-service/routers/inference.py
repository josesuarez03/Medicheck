from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.bedrock_claude import build_turn_prompt, call_claude
from services.chatbot import Chatbot
from services.comprehend_medical import detect_entities
from services.embeddings import build_embedding_payload, generate_embedding
from services.input_validate import analyze_message
from services.medical_facts import FactsSummary, MedicalFact


router = APIRouter(prefix="/inference", tags=["inference"])


class InferenceRequest(BaseModel):
    message: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    user_data: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None
    conversation_id: str | None = None


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "bedrock": "configured",
        "entities": "available",
        "service": "ai-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/chat")
async def infer_chat(payload: InferenceRequest) -> dict[str, Any]:
    chatbot = Chatbot(
        payload.message,
        payload.user_data or payload.context,
        user_id=payload.user_id,
        conversation_id=payload.conversation_id,
        existing_context=payload.context,
    )
    result = chatbot.initialize_conversation()
    return {
        "status": "ok",
        "service": "ai-service",
        "message": payload.message,
        "conversation_id": payload.conversation_id,
        **result,
    }


@router.post("/comprehend")
async def infer_comprehend(payload: InferenceRequest) -> dict[str, Any]:
    result = detect_entities(payload.message, context=payload.context)
    return result


@router.post("/embed")
async def infer_embed(payload: InferenceRequest) -> dict[str, Any]:
    extraction = detect_entities(payload.message, context=payload.context)
    analysis = analyze_message(payload.message)
    facts = [MedicalFact(**fact) for fact in extraction.get("facts", [])]
    facts_summary = FactsSummary(**(extraction.get("facts_summary", {}) or {}))
    embedding_payload = build_embedding_payload(payload.message, facts, analysis, facts_summary)
    embedding = generate_embedding(embedding_payload.embedding_text) if not embedding_payload.skipped else []
    return {
        "embedding": embedding,
        "embedding_target": embedding_payload.embedding_target,
        "embedding_text": embedding_payload.embedding_text,
        "signal_score": embedding_payload.signal_score,
        "skipped": embedding_payload.skipped,
        "reason": embedding_payload.reason,
    }


@router.post("/consult")
async def infer_consult(payload: InferenceRequest) -> dict[str, Any]:
    try:
        prompt_bundle = {
            "user_input": payload.message,
            "postgres_context": payload.context,
            "facts_summary": {},
            "questions_selected": [],
        }
        prompt_meta = build_turn_prompt(
            prompt_bundle,
            initial_prompt="Responde como asistente clínico orientativo, sin diagnosticar ni prescribir.",
        )
        response = call_claude(
            prompt=prompt_bundle,
            initial_prompt="Responde como asistente clínico orientativo, sin diagnosticar ni prescribir.",
            temperature=0.2,
        )
    except Exception:
        response = "No se pudo completar la consulta libre en este momento."
        prompt_meta = {
            "prompt_sections_used": [],
            "prompt_token_budget": {"target_max_input_tokens": 1200, "used_estimate": 0},
        }
    return {
        "status": "ok",
        "service": "ai-service",
        "mode": "consultation",
        "message": payload.message,
        "response": response,
        "prompt_sections_used": prompt_meta["prompt_sections_used"],
        "prompt_token_budget": prompt_meta["prompt_token_budget"],
    }
