import os
from typing import Any
import uuid
from urllib.parse import urlparse

import asyncio
from services.etl_dispatcher import clear_inactivity_token, enqueue_etl_dispatch, schedule_inactivity_etl

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None


AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:5001")
EXPERT_SERVICE_URL = os.getenv("EXPERT_SERVICE_URL", "http://expert-service:5002")


def _resolve_service_url(raw_url: str | None, *, env_var: str) -> str:
    base_url = (raw_url or "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError(f"La variable {env_var} no está configurada.")

    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(
            f"La variable {env_var} debe incluir una URL absoluta con http:// o https://. Valor actual: {raw_url!r}"
        )
    return base_url


def _build_service_url(raw_url: str | None, path: str, *, env_var: str) -> str:
    base_url = _resolve_service_url(raw_url, env_var=env_var)
    normalized_path = f"/{path.lstrip('/')}"
    return f"{base_url}{normalized_path}"


async def forward_to_ai(payload: dict[str, Any], path: str = "/inference/chat") -> dict[str, Any]:
    if httpx is None:
        raise RuntimeError("httpx no está disponible en este entorno.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(_build_service_url(AI_SERVICE_URL, path, env_var="AI_SERVICE_URL"), json=payload)
        response.raise_for_status()
        return response.json()


async def forward_to_ai_request(
    *,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if httpx is None:
        raise RuntimeError("httpx no está disponible en este entorno.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method=method,
            url=_build_service_url(AI_SERVICE_URL, path, env_var="AI_SERVICE_URL"),
            params=params,
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def forward_to_expert(payload: dict[str, Any], path: str = "/expert/triage") -> dict[str, Any]:
    if httpx is None:
        raise RuntimeError("httpx no está disponible en este entorno.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(_build_service_url(EXPERT_SERVICE_URL, path, env_var="EXPERT_SERVICE_URL"), json=payload)
        response.raise_for_status()
        return response.json()


async def orchestrate_chat(payload: dict[str, Any]) -> dict[str, Any]:
    conversation_id = payload.get("conversation_id") or str(uuid.uuid4())
    user_id = payload.get("user_id")
    jwt_token = payload.get("jwt_token")
    ai_payload = {
        **payload,
        "conversation_id": conversation_id,
    }
    expert_payload = {
        "message": payload.get("message", ""),
        "context": payload.get("context", {}),
    }
    expert_result, ai_result = await asyncio.gather(
        forward_to_expert(expert_payload),
        forward_to_ai(ai_payload),
    )

    if expert_result.get("emergency_triggered"):
        return {
            "status": "ok",
            "service": "gateway",
            "conversation_id": conversation_id,
            "response_source": "expert",
            "response": expert_result.get("response", ""),
            "triaje_level": expert_result.get("triage_level", "Severo"),
            "expert": expert_result,
            "ai": ai_result,
        }

    etl_dispatch = None
    ai_conversation_state = ai_result.get("conversation_state", {}) if isinstance(ai_result, dict) else {}
    if isinstance(ai_conversation_state, dict) and user_id and conversation_id:
        if ai_conversation_state.get("should_trigger_etl") is True:
            clear_inactivity_token(user_id=user_id, conversation_id=conversation_id)
            etl_dispatch = enqueue_etl_dispatch(
                user_id=user_id,
                conversation_id=conversation_id,
                jwt_token=jwt_token,
                reasons=[str(ai_conversation_state.get("etl_reason") or "closure_confirmed")],
            )
            ai_conversation_state["etl_dispatch"] = etl_dispatch
        elif ai_conversation_state.get("awaiting_closure_confirmation") is True:
            etl_dispatch = schedule_inactivity_etl(
                user_id=user_id,
                conversation_id=conversation_id,
                jwt_token=jwt_token,
                reasons=["inactivity_timeout"],
            )
            ai_conversation_state["etl_dispatch"] = etl_dispatch
        else:
            clear_inactivity_token(user_id=user_id, conversation_id=conversation_id)

    return {
        "status": "ok",
        "service": "gateway",
        "conversation_id": conversation_id,
        "response_source": "ai",
        "response": ai_result.get("response", ""),
        "final_chat_summary": ai_result.get("final_chat_summary"),
        "final_chat_summary_title": ai_result.get("final_chat_summary_title"),
        "triaje_level": ai_result.get("triaje_level") or expert_result.get("triage_level", "Leve"),
        "expert": expert_result,
        "ai": ai_result,
        "conversation_state": ai_conversation_state,
        "etl_dispatch": etl_dispatch,
    }
