from celery.utils.log import get_task_logger

from celery_app import celery_app
from data.connect import worker_redis_client
from services.etl_runner import execute_etl_once


logger = get_task_logger(__name__)


def _inactivity_key(user_id: str, conversation_id: str) -> str:
    return f"gateway:etl:inactivity:{user_id}:{conversation_id}"


@celery_app.task(
    bind=True,
    name="tasks.etl_tasks.run_etl_for_conversation",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_etl_for_conversation(self, payload: dict) -> dict:
    logger.info("ETL task received for conversation %s", payload.get("conversation_id"))
    return execute_etl_once(
        user_id=payload["user_id"],
        conversation_id=payload["conversation_id"],
        jwt_token=payload.get("jwt_token"),
        django_api_url=payload.get("django_api_url"),
        run_id=payload.get("run_id"),
        reasons=payload.get("reasons"),
    )


@celery_app.task(
    bind=True,
    name="tasks.etl_tasks.trigger_etl_if_still_inactive",
)
def trigger_etl_if_still_inactive(self, payload: dict) -> dict:
    user_id = payload["user_id"]
    conversation_id = payload["conversation_id"]
    expected_token = payload.get("inactivity_token")
    current_token = worker_redis_client.get(_inactivity_key(user_id, conversation_id))
    if not expected_token or current_token != expected_token:
        logger.info(
            "Skipping inactivity ETL for conversation %s because a newer activity token exists",
            conversation_id,
        )
        return {"success": False, "skipped": True, "reason": "stale_inactivity_token"}

    worker_redis_client.delete(_inactivity_key(user_id, conversation_id))
    return execute_etl_once(
        user_id=user_id,
        conversation_id=conversation_id,
        jwt_token=payload.get("jwt_token"),
        django_api_url=payload.get("django_api_url"),
        run_id=payload.get("run_id"),
        reasons=payload.get("reasons") or ["inactivity_timeout"],
    )
