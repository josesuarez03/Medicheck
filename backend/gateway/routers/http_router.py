from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from middleware.auth import get_bearer_token


router = APIRouter(tags=["http"])


class EtlRetryRequest(BaseModel):
    conversation_id: str
    user_id: str


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "scaffold",
        "service": "gateway",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/conversation/etl/retry")
async def retry_etl(
    payload: EtlRetryRequest,
    bearer_token: str | None = Depends(get_bearer_token),
) -> dict[str, str | None]:
    return {
        "status": "pending",
        "service": "gateway",
        "conversation_id": payload.conversation_id,
        "user_id": payload.user_id,
        "token_present": "yes" if bearer_token else "no",
    }
