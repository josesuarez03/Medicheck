from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.comprehend_medical import detect_entities
from services.embeddings import generate_embedding


router = APIRouter(prefix="/inference", tags=["inference"])


class InferenceRequest(BaseModel):
    message: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None
    conversation_id: str | None = None


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "bedrock": "pending",
        "mongo": "pending",
        "service": "ai-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/chat")
async def infer_chat(payload: InferenceRequest) -> dict[str, Any]:
    return {
        "status": "pending",
        "service": "ai-service",
        "message": payload.message,
        "conversation_id": payload.conversation_id,
        "notes": "Los modulos copiados desde Flask estan disponibles para la migracion progresiva.",
    }


@router.post("/comprehend")
async def infer_comprehend(payload: InferenceRequest) -> dict[str, Any]:
    return {
        "entities": detect_entities(payload.message),
    }


@router.post("/embed")
async def infer_embed(payload: InferenceRequest) -> dict[str, Any]:
    return {
        "embedding": generate_embedding(payload.message),
    }


@router.post("/consult")
async def infer_consult(payload: InferenceRequest) -> dict[str, Any]:
    return {
        "status": "pending",
        "service": "ai-service",
        "mode": "consultation",
        "message": payload.message,
    }
