import json
import os
from typing import Any

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
ETL_QUEUE = os.getenv("ETL_QUEUE", "etl_queue")
ETL_DEAD_LETTER_EXCHANGE = os.getenv("ETL_DEAD_LETTER_EXCHANGE", "etl_dead_letter")
ETL_MAX_RETRIES = max(1, int(os.getenv("ETL_MAX_RETRIES", "5")))


def _declare_queue(channel) -> None:
    channel.exchange_declare(exchange=ETL_DEAD_LETTER_EXCHANGE, exchange_type="fanout", durable=True)
    channel.queue_declare(
        queue=ETL_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": ETL_DEAD_LETTER_EXCHANGE,
            "x-message-ttl": 86400000,
        },
    )


def _process_payload(payload: dict[str, Any]) -> dict[str, Any]:
    from services.etl_runner import execute_etl_once

    return execute_etl_once(
        user_id=payload["user_id"],
        conversation_id=payload["conversation_id"],
        jwt_token=payload.get("jwt_token"),
        django_api_url=payload.get("django_api_url"),
    )


def _callback(channel, method, _, body: bytes) -> None:
    payload = json.loads(body.decode("utf-8"))
    try:
        result = _process_payload(payload)
    except Exception:
        result = {"success": False}
    attempts = 0
    headers = getattr(method, "headers", None) or {}
    x_death = headers.get("x-death", [])
    if isinstance(x_death, list) and x_death:
        attempts = int(x_death[0].get("count", 0))
    if result.get("success"):
        channel.basic_ack(delivery_tag=method.delivery_tag)
    else:
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=(attempts + 1 < ETL_MAX_RETRIES))


def main() -> None:
    import pika

    parameters = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    _declare_queue(channel)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=ETL_QUEUE, on_message_callback=_callback)
    channel.start_consuming()


if __name__ == "__main__":
    main()
