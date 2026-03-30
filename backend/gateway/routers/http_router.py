from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from middleware.auth import get_bearer_token
from middleware.rate_limit import enforce_rate_limit
from services.orchestrator import orchestrate_chat


router = APIRouter(tags=["http"])


class EtlRetryRequest(BaseModel):
    conversation_id: str
    user_id: str


class ChatRequest(BaseModel):
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    user_data: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = None


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "scaffold",
        "service": "gateway",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    request: Request,
    bearer_token: dict | None = Depends(get_bearer_token),
) -> dict:
    await enforce_rate_limit(request, scope="http")
    ai_payload = {
        "message": payload.message,
        "context": payload.context,
        "user_data": payload.user_data,
        "conversation_id": payload.conversation_id,
        "user_id": (bearer_token or {}).get("user_id") or (bearer_token or {}).get("sub"),
    }
    if bearer_token and bearer_token.get("raw_token"):
        ai_payload["jwt_token"] = bearer_token["raw_token"]
    return await orchestrate_chat(ai_payload)


@router.post("/conversation/etl/retry")
async def retry_etl(
    payload: EtlRetryRequest,
    bearer_token: dict | None = Depends(get_bearer_token),
) -> dict[str, str | None]:
    if not bearer_token:
        raise HTTPException(status_code=401, detail="Se requiere autenticación para reintentar ETL.")
    return {
        "status": "not_implemented",
        "service": "gateway",
        "conversation_id": payload.conversation_id,
        "user_id": payload.user_id,
        "token_present": "yes",
    }
