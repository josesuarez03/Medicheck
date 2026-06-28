from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from middleware.auth import get_bearer_token
from middleware.rate_limit import enforce_rate_limit
from services.etl_dispatcher import clear_inactivity_token, enqueue_etl_dispatch
from services.orchestrator import orchestrate_chat, forward_to_ai_request


router = APIRouter(tags=["http"])


class EtlRetryRequest(BaseModel):
    conversation_id: str
    user_id: str | None = None


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


def _require_user_id(bearer_token: dict | None) -> str:
    user_id = (bearer_token or {}).get("user_id") or (bearer_token or {}).get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Se requiere autenticación para esta operación.")
    return str(user_id)


@router.get("/chat/conversations")
async def get_conversations(
    view: str = "active",
    bearer_token: dict | None = Depends(get_bearer_token),
) -> dict:
    user_id = _require_user_id(bearer_token)
    return await forward_to_ai_request(
        method="GET",
        path="/inference/conversations",
        params={"user_id": user_id, "view": view},
    )


@router.get("/chat/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    bearer_token: dict | None = Depends(get_bearer_token),
) -> dict:
    user_id = _require_user_id(bearer_token)
    return await forward_to_ai_request(
        method="GET",
        path=f"/inference/conversation/{conversation_id}",
        params={"user_id": user_id},
    )


@router.delete("/chat/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    bearer_token: dict | None = Depends(get_bearer_token),
) -> dict:
    user_id = _require_user_id(bearer_token)
    return await forward_to_ai_request(
        method="DELETE",
        path=f"/inference/conversation/{conversation_id}",
        params={"user_id": user_id},
    )


@router.post("/chat/conversation/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    bearer_token: dict | None = Depends(get_bearer_token),
) -> dict:
    user_id = _require_user_id(bearer_token)
    return await forward_to_ai_request(
        method="POST",
        path=f"/inference/conversation/{conversation_id}/archive",
        params={"user_id": user_id},
    )


@router.post("/chat/conversation/{conversation_id}/recover")
async def recover_conversation(
    conversation_id: str,
    bearer_token: dict | None = Depends(get_bearer_token),
) -> dict:
    user_id = _require_user_id(bearer_token)
    return await forward_to_ai_request(
        method="POST",
        path=f"/inference/conversation/{conversation_id}/recover",
        params={"user_id": user_id},
    )


@router.delete("/chat/conversations")
async def delete_all_conversations(
    bearer_token: dict | None = Depends(get_bearer_token),
) -> dict:
    user_id = _require_user_id(bearer_token)
    return await forward_to_ai_request(
        method="DELETE",
        path="/inference/conversations",
        params={"user_id": user_id},
    )


@router.post("/conversation/etl/retry")
async def retry_etl(
    payload: EtlRetryRequest,
    bearer_token: dict | None = Depends(get_bearer_token),
) -> dict[str, str | None]:
    if not bearer_token:
        raise HTTPException(status_code=401, detail="Se requiere autenticación para reintentar ETL.")
    user_id = (bearer_token or {}).get("user_id") or (bearer_token or {}).get("sub") or payload.user_id
    if not user_id:
        raise HTTPException(status_code=400, detail="No se pudo resolver el usuario autenticado.")
    clear_inactivity_token(user_id=user_id, conversation_id=payload.conversation_id)
    dispatch = enqueue_etl_dispatch(
        user_id=user_id,
        conversation_id=payload.conversation_id,
        jwt_token=(bearer_token or {}).get("raw_token"),
        reasons=["manual_retry"],
    )
    return {
        "status": dispatch.get("status", "queued"),
        "service": "gateway",
        "conversation_id": payload.conversation_id,
        "user_id": user_id,
        "token_present": "yes",
        "task_id": dispatch.get("task_id"),
        "run_id": dispatch.get("run_id"),
    }
