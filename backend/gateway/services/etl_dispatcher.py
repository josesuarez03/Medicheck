from __future__ import annotations

import os
import uuid
from typing import Any

from celery import Celery
import redis


_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    f"amqp://{os.getenv('RABBITMQ_DEFAULT_USER', 'guest')}:{os.getenv('RABBITMQ_DEFAULT_PASS', 'guest')}@rabbitmq:5672//",
)
_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    f"redis://:{os.getenv('REDIS_PASSWORD', '')}@{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/{os.getenv('REDIS_DB_WORKER', '3')}",
)
_ETL_QUEUE = os.getenv("ETL_QUEUE", "etl_queue")
_REDIS_HOST = os.getenv("REDIS_HOST", "redis")
_REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
_REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
_REDIS_DB_WORKER = int(os.getenv("REDIS_DB_WORKER", "3"))
_ETL_INACTIVITY_SECONDS = max(30, int(os.getenv("ETL_INACTIVITY_SECONDS", "900")))

celery_client = Celery("gateway_etl_dispatcher", broker=_BROKER_URL, backend=_RESULT_BACKEND or None)


def _redis_client():
    return redis.Redis(
        host=_REDIS_HOST,
        port=_REDIS_PORT,
        password=_REDIS_PASSWORD,
        db=_REDIS_DB_WORKER,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def _inactivity_key(user_id: str, conversation_id: str) -> str:
    return f"gateway:etl:inactivity:{user_id}:{conversation_id}"


def mark_inactivity_token(*, user_id: str, conversation_id: str) -> str:
    token = str(uuid.uuid4())
    _redis_client().set(_inactivity_key(user_id, conversation_id), token, ex=_ETL_INACTIVITY_SECONDS * 4)
    return token


def clear_inactivity_token(*, user_id: str, conversation_id: str) -> None:
    _redis_client().delete(_inactivity_key(user_id, conversation_id))


def enqueue_etl_dispatch(
    *,
    user_id: str,
    conversation_id: str,
    jwt_token: str | None = None,
    reasons: list[str] | None = None,
    django_api_url: str | None = None,
) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "jwt_token": jwt_token,
        "run_id": run_id,
        "reasons": list(dict.fromkeys(reasons or ["closure_confirmed"])),
        "django_api_url": django_api_url,
    }
    task = celery_client.send_task(
        "tasks.etl_tasks.run_etl_for_conversation",
        kwargs={"payload": payload},
        queue=_ETL_QUEUE,
    )
    return {
        "status": "queued",
        "task_id": task.id,
        "run_id": run_id,
        "queue": _ETL_QUEUE,
    }


def schedule_inactivity_etl(
    *,
    user_id: str,
    conversation_id: str,
    jwt_token: str | None = None,
    reasons: list[str] | None = None,
    django_api_url: str | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    inactivity_seconds = max(30, int(timeout_seconds or _ETL_INACTIVITY_SECONDS))
    token = mark_inactivity_token(user_id=user_id, conversation_id=conversation_id)
    run_id = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "jwt_token": jwt_token,
        "run_id": run_id,
        "reasons": list(dict.fromkeys(reasons or ["inactivity_timeout"])),
        "django_api_url": django_api_url,
        "inactivity_token": token,
    }
    task = celery_client.send_task(
        "tasks.etl_tasks.trigger_etl_if_still_inactive",
        kwargs={"payload": payload},
        queue=_ETL_QUEUE,
        countdown=inactivity_seconds,
    )
    return {
        "status": "scheduled",
        "task_id": task.id,
        "run_id": run_id,
        "queue": _ETL_QUEUE,
        "inactivity_seconds": inactivity_seconds,
        "inactivity_token": token,
    }
