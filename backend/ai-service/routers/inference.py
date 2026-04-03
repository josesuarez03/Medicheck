from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
import hmac
import hashlib
import json

from services.bedrock_claude import build_turn_prompt, call_claude
from services.chatbot import Chatbot
from services.comprehend_medical import detect_entities
from services.conversation_context_service import ConversationContextService
from services.embeddings import build_embedding_payload, generate_embedding
from services.input_validate import analyze_message
from services.medical_facts import FactsSummary, MedicalFact
from models.conversation import ConversationalDatasetManager
from config.config import Config


router = APIRouter(prefix="/inference", tags=["inference"])


class InferenceRequest(BaseModel):
    message: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    user_data: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None
    conversation_id: str | None = None


class UserSummaryUpsertRequest(BaseModel):
    user_id: str
    patient_id: str
    clinical_summary_id: str
    summary_version: int
    summary_text: str
    clinical_snapshot: dict[str, Any] = Field(default_factory=dict)


conversation_manager = ConversationalDatasetManager()


def _is_valid_internal_request(payload: dict[str, Any], request_timestamp: str | None, request_signature: str | None) -> bool:
    shared_secret = Config.FLASK_API_KEY or ""
    if not request_timestamp or not request_signature or not shared_secret:
        return False
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    expected_signature = hmac.new(
        shared_secret.encode("utf-8"),
        f"{request_timestamp}:{canonical_payload}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, request_signature)


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
        "conversation_id": result.get("conversation_id") or payload.conversation_id,
        **result,
    }


@router.get("/conversations")
async def list_conversations(user_id: str, view: str = "active") -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "ai-service",
        "conversations": conversation_manager.get_conversations(user_id=user_id, view=view),
    }


@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str, user_id: str) -> dict[str, Any]:
    conversation = conversation_manager.get_conversation(user_id=user_id, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    return {
        "status": "ok",
        "service": "ai-service",
        "conversation": conversation,
    }


@router.post("/conversation/{conversation_id}/archive")
async def archive_conversation(conversation_id: str, user_id: str) -> dict[str, Any]:
    updated = conversation_manager.archive_conversation(user_id=user_id, conversation_id=conversation_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Conversación no encontrada o ya archivada.")
    return {"status": "ok", "service": "ai-service", "conversation_id": conversation_id}


@router.post("/conversation/{conversation_id}/recover")
async def recover_conversation(conversation_id: str, user_id: str) -> dict[str, Any]:
    updated = conversation_manager.recover_conversation(user_id=user_id, conversation_id=conversation_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Conversación no encontrada o no archivada.")
    return {"status": "ok", "service": "ai-service", "conversation_id": conversation_id}


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str) -> dict[str, Any]:
    updated = conversation_manager.delete_conversation(user_id=user_id, conversation_id=conversation_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    return {"status": "ok", "service": "ai-service", "conversation_id": conversation_id}


@router.delete("/conversations")
async def delete_all_conversations(user_id: str) -> dict[str, Any]:
    deleted = conversation_manager.delete_all_conversations(user_id=user_id)
    return {"status": "ok", "service": "ai-service", "deleted_count": deleted}


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


@router.post("/internal/user-summary/upsert")
async def upsert_user_summary_embedding(
    payload: UserSummaryUpsertRequest,
    x_request_timestamp: str | None = Header(default=None),
    x_request_signature: str | None = Header(default=None),
) -> dict[str, Any]:
    body = payload.model_dump()
    if not _is_valid_internal_request(body, x_request_timestamp, x_request_signature):
        return {"status": "error", "service": "ai-service", "reason": "invalid_internal_signature"}

    summary_text = payload.summary_text.strip()
    if not summary_text:
        return {"status": "ok", "service": "ai-service", "skipped": True, "reason": "empty_summary_text"}

    context_service = ConversationContextService()
    embedding = generate_embedding(summary_text)
    context_service.vector_store.upsert_user_summary_embedding(
        user_id=payload.user_id,
        patient_id=payload.patient_id,
        clinical_summary_id=payload.clinical_summary_id,
        embedding_model=Config.BEDROCK_EMBEDDING_MODEL_ID or "deterministic_fallback",
        embedding=embedding,
        summary_text=summary_text,
        clinical_snapshot=payload.clinical_snapshot,
        summary_version=payload.summary_version,
        source_updated_at=datetime.now(timezone.utc),
    )
    return {"status": "ok", "service": "ai-service", "skipped": False}
