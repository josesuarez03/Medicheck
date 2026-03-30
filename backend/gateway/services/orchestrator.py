import os
from typing import Any

import httpx


AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:5001")
EXPERT_SERVICE_URL = os.getenv("EXPERT_SERVICE_URL", "http://expert-service:5002")


async def forward_to_ai(payload: dict[str, Any], path: str = "/inference/chat") -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{AI_SERVICE_URL}{path}", json=payload)
        response.raise_for_status()
        return response.json()


async def forward_to_expert(payload: dict[str, Any], path: str = "/expert/triage") -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{EXPERT_SERVICE_URL}{path}", json=payload)
        response.raise_for_status()
        return response.json()
