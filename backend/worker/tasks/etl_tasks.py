from celery.utils.log import get_task_logger

from celery_app import celery_app
from services.etl_runner import execute_etl_once


logger = get_task_logger(__name__)


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
