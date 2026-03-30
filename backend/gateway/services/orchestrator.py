import os
from typing import Any

import asyncio

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None


AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:5001")
EXPERT_SERVICE_URL = os.getenv("EXPERT_SERVICE_URL", "http://expert-service:5002")


async def forward_to_ai(payload: dict[str, Any], path: str = "/inference/chat") -> dict[str, Any]:
    if httpx is None:
        raise RuntimeError("httpx no está disponible en este entorno.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{AI_SERVICE_URL}{path}", json=payload)
        response.raise_for_status()
        return response.json()


async def forward_to_expert(payload: dict[str, Any], path: str = "/expert/triage") -> dict[str, Any]:
    if httpx is None:
        raise RuntimeError("httpx no está disponible en este entorno.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{EXPERT_SERVICE_URL}{path}", json=payload)
        response.raise_for_status()
        return response.json()


async def orchestrate_chat(payload: dict[str, Any]) -> dict[str, Any]:
    expert_payload = {
        "message": payload.get("message", ""),
        "context": payload.get("context", {}),
    }
    expert_result, ai_result = await asyncio.gather(
        forward_to_expert(expert_payload),
        forward_to_ai(payload),
    )

    if expert_result.get("emergency_triggered"):
        return {
            "status": "ok",
            "service": "gateway",
            "response_source": "expert",
            "response": expert_result.get("response", ""),
            "triaje_level": expert_result.get("triage_level", "Severo"),
            "expert": expert_result,
            "ai": ai_result,
        }

    return {
        "status": "ok",
        "service": "gateway",
        "response_source": "ai",
        "response": ai_result.get("response", ""),
        "triaje_level": ai_result.get("triaje_level") or expert_result.get("triage_level", "Leve"),
        "expert": expert_result,
        "ai": ai_result,
    }
