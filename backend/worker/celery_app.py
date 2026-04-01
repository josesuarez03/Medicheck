from celery import Celery
from kombu import Queue

from config.config import Config


celery_app = Celery(
    "hipo_worker",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND or None,
    include=[
        "tasks.chat_tasks",
        "tasks.etl_tasks",
    ],
)

celery_app.conf.update(
    task_default_queue=Config.CHAT_QUEUE_NAME,
    task_queues=(
        Queue(Config.CHAT_QUEUE_NAME),
        Queue(Config.ETL_QUEUE_NAME),
    ),
    task_routes={
        "tasks.chat_tasks.process_chat_message": {"queue": Config.CHAT_QUEUE_NAME},
        "tasks.etl_tasks.run_etl_for_conversation": {"queue": Config.ETL_QUEUE_NAME},
    },
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
