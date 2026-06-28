import requests
from celery.utils.log import get_task_logger

from celery_app import celery_app
from config.config import Config


logger = get_task_logger(__name__)


def _chat_url() -> str:
    base = Config.AI_SERVICE_URL.rstrip("/")
    path = f"/{Config.AI_SERVICE_CHAT_PATH.lstrip('/')}"
    return f"{base}{path}"


@celery_app.task(
    bind=True,
    name="tasks.chat_tasks.process_chat_message",
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_chat_message(self, payload: dict) -> dict:
    logger.info("Chat task received for conversation %s", payload.get("conversation_id"))
    response = requests.post(_chat_url(), json=payload, timeout=30)
    response.raise_for_status()
    return response.json()
