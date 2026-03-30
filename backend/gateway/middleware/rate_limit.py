import os
import time

import redis
from fastapi import HTTPException, Request


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("GATEWAY_RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("GATEWAY_RATE_LIMIT_MAX_REQUESTS", "30"))


def _redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def _key(scope: str, identity: str) -> str:
    now_bucket = int(time.time() // RATE_LIMIT_WINDOW_SECONDS)
    return f"gateway:rate:{scope}:{identity}:{now_bucket}"


async def enforce_rate_limit(request: Request, scope: str = "http") -> None:
    identity = request.client.host if request.client else "unknown"
    key = _key(scope, identity)
    try:
        client = _redis_client()
        current = client.incr(key)
        if current == 1:
            client.expire(key, RATE_LIMIT_WINDOW_SECONDS)
    except Exception:
        return
    if current > RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit excedido.")
