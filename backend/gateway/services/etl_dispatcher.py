from __future__ import annotations

import os
import uuid
from typing import Any

from celery import Celery


_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    f"amqp://{os.getenv('RABBITMQ_DEFAULT_USER', 'guest')}:{os.getenv('RABBITMQ_DEFAULT_PASS', 'guest')}@rabbitmq:5672//",
)
_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    f"redis://:{os.getenv('REDIS_PASSWORD', '')}@{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/{os.getenv('REDIS_DB_WORKER', '3')}",
)
_ETL_QUEUE = os.getenv("ETL_QUEUE", "etl_queue")

celery_client = Celery("gateway_etl_dispatcher", broker=_BROKER_URL, backend=_RESULT_BACKEND or None)


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
