import json
import logging
import os
import threading
import time
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from config.config import Config
from data.connect import worker_redis_client
from models.conversation import ConversationalDatasetManager
from services.medical_data import MedicalDataProcessor
from services.send_api import send_data_to_django

logger = logging.getLogger(__name__)

_RETRY_BACKOFF_SECONDS: Tuple[int, int, int] = (0, 2, 5)
_REGISTRY_LOCK = threading.Lock()
_CONVERSATION_QUEUES: Dict[str, Deque[Dict[str, Any]]] = {}
_ACTIVE_WORKERS: Set[str] = set()
_INACTIVITY_LOCK = threading.Lock()
_INACTIVITY_TIMERS: Dict[str, threading.Timer] = {}
_DEFAULT_INACTIVITY_SECONDS = max(1, int(os.getenv("ETL_INACTIVITY_SECONDS", "900")))


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def _conversation_key(user_id: str, conversation_id: str) -> str:
    return f"{user_id}:{conversation_id}"


def _log_etl_event(event_name: str, **payload: Any) -> None:
    logger.info("%s %s", event_name, json.dumps(payload, ensure_ascii=False))


def _update_etl_state(user_id: str, conversation_id: str, etl_state: Dict[str, Any]) -> None:
    manager = ConversationalDatasetManager()
    manager.update_conversation_etl_state(user_id, conversation_id, etl_state)


def _etl_lock_key(user_id: str, conversation_id: str) -> str:
    return f"worker:etl:lock:{user_id}:{conversation_id}"


def _etl_cache_key(user_id: str, conversation_id: str) -> str:
    return f"worker:etl:cache:{user_id}:{conversation_id}"


def _read_cached_etl_result(user_id: str, conversation_id: str) -> Dict[str, Any] | None:
    try:
        raw = worker_redis_client.get(_etl_cache_key(user_id, conversation_id))
        if not raw:
            return None
        cached = json.loads(raw)
        return cached if isinstance(cached, dict) else None
    except Exception as exc:
        logger.warning("No se pudo leer caché ETL %s/%s: %s", user_id, conversation_id, str(exc))
        return None


def _write_cached_etl_result(user_id: str, conversation_id: str, medical_data: Dict[str, Any]) -> None:
    payload = {
        "medical_data": medical_data,
        "cached_at": _utc_now_iso(),
    }
    worker_redis_client.set(
        _etl_cache_key(user_id, conversation_id),
        json.dumps(payload, ensure_ascii=False),
        ex=Config.ETL_CACHE_TTL_SECONDS,
    )


def _should_reuse_cached_etl(reasons: List[str]) -> bool:
    reusable_reasons = {"manual_retry", "inactivity_timeout", "closure_confirmed", "retry_after_failure"}
    return bool(set(reasons or []) & reusable_reasons)


def _acquire_etl_lock(user_id: str, conversation_id: str, run_id: str) -> bool:
    return bool(
        worker_redis_client.set(
            _etl_lock_key(user_id, conversation_id),
            run_id,
            nx=True,
            ex=Config.ETL_LOCK_TTL_SECONDS,
        )
    )


def _release_etl_lock(user_id: str, conversation_id: str, run_id: str) -> None:
    key = _etl_lock_key(user_id, conversation_id)
    try:
        current = worker_redis_client.get(key)
        if current == run_id:
            worker_redis_client.delete(key)
    except Exception as exc:
        logger.warning("No se pudo liberar lock ETL %s: %s", key, str(exc))


def _resolve_dispatch_mode() -> str:
    mode = (Config.ETL_DISPATCH_MODE or "celery").strip().lower()
    if mode not in {"celery", "threading"}:
        return "celery"
    return mode


def _dispatch_via_celery(task: Dict[str, Any]) -> None:
    from celery_app import celery_app

    celery_app.send_task(
        "tasks.etl_tasks.run_etl_for_conversation",
        kwargs={"payload": task},
        queue=Config.ETL_QUEUE_NAME,
    )


def _dispatch_via_threading(task: Dict[str, Any]) -> None:
    queue_key = _conversation_key(task["user_id"], task["conversation_id"])
    with _REGISTRY_LOCK:
        queue = _CONVERSATION_QUEUES.setdefault(queue_key, deque())
        queue.append(task)
        should_start_worker = queue_key not in _ACTIVE_WORKERS
        if should_start_worker:
            _ACTIVE_WORKERS.add(queue_key)

    if should_start_worker:
        worker_name = f"etl-worker-{abs(hash(queue_key)) % 100000}"
        threading.Thread(
            target=_worker_for_conversation,
            args=(queue_key,),
            daemon=True,
            name=worker_name,
        ).start()


def execute_etl_once(
    user_id: str,
    conversation_id: str,
    jwt_token: Optional[str] = None,
    django_api_url: Optional[str] = None,
    run_id: Optional[str] = None,
    reasons: Optional[List[str]] = None,
) -> Dict[str, Any]:
    resolved_run_id = run_id or str(uuid.uuid4())
    resolved_reasons = list(dict.fromkeys(reasons or []))
    if not _acquire_etl_lock(user_id, conversation_id, resolved_run_id):
        _log_etl_event(
            "etl_skipped_already_running",
            user_id=user_id,
            conversation_id=conversation_id,
            run_id=resolved_run_id,
            reasons=resolved_reasons,
        )
        return {
            "success": False,
            "skipped": True,
            "error": "ETL ya en ejecución para esta conversación.",
            "medical_data": None,
            "django_response": None,
        }

    processor = MedicalDataProcessor(user_id=user_id, conversation_id=conversation_id)
    try:
        cached = _read_cached_etl_result(user_id, conversation_id) if _should_reuse_cached_etl(resolved_reasons) else None
        medical_data = cached.get("medical_data") if isinstance(cached, dict) else None
        if medical_data:
            _log_etl_event(
                "etl_cache_hit",
                user_id=user_id,
                conversation_id=conversation_id,
                run_id=resolved_run_id,
                reasons=resolved_reasons,
            )
        else:
            medical_data = processor.process_medical_data(user_id, conversation_id)
        if not medical_data or "error" in medical_data:
            error_msg = (medical_data or {}).get("error", "No se pudo procesar la conversación.")
            return {
                "success": False,
                "error": error_msg,
                "medical_data": medical_data,
                "django_response": None,
            }
        if not cached:
            _write_cached_etl_result(user_id, conversation_id, medical_data)

        django_response = send_data_to_django(
            user_id,
            medical_data,
            jwt_token=jwt_token,
            base_url=django_api_url,
        )
        has_error = isinstance(django_response, dict) and bool(django_response.get("error"))
        return {
            "success": not has_error,
            "error": django_response.get("error") if has_error else "",
            "medical_data": medical_data,
            "django_response": django_response,
            "cache_used": bool(cached),
        }
    finally:
        _release_etl_lock(user_id, conversation_id, resolved_run_id)


def _execute_task_with_retries(
    task: Dict[str, Any],
    backoff_seconds: Tuple[int, ...] = _RETRY_BACKOFF_SECONDS,
) -> Dict[str, Any]:
    user_id = task["user_id"]
    conversation_id = task["conversation_id"]
    run_id = task["run_id"]
    reasons = list(task.get("reasons") or [])
    jwt_token = task.get("jwt_token")
    django_api_url = task.get("django_api_url")

    last_result: Dict[str, Any] = {
        "success": False,
        "error": "No se ejecutó la ETL.",
        "medical_data": None,
        "django_response": None,
    }

    for attempt, delay in enumerate(backoff_seconds, start=1):
        if delay > 0:
            _log_etl_event(
                "etl_retry_scheduled",
                user_id=user_id,
                conversation_id=conversation_id,
                run_id=run_id,
                reasons=reasons,
                attempt=attempt,
                delay_seconds=delay,
            )
            time.sleep(delay)

        now_iso = _utc_now_iso()
        _update_etl_state(
            user_id,
            conversation_id,
            {
                "last_status": "running",
                "attempts": attempt,
                "last_attempt_at": now_iso,
                "last_run_id": run_id,
                "last_reasons": reasons,
                "last_error": "",
            },
        )
        _log_etl_event(
            "etl_attempt",
            user_id=user_id,
            conversation_id=conversation_id,
            run_id=run_id,
            reasons=reasons,
            attempt=attempt,
        )

        last_result = execute_etl_once(
            user_id=user_id,
            conversation_id=conversation_id,
            jwt_token=jwt_token,
            django_api_url=django_api_url,
            run_id=run_id,
            reasons=reasons,
        )
        if last_result.get("success"):
            success_time = _utc_now_iso()
            _update_etl_state(
                user_id,
                conversation_id,
                {
                    "last_status": "success",
                    "attempts": attempt,
                    "last_attempt_at": success_time,
                    "last_success_at": success_time,
                    "last_run_id": run_id,
                    "last_reasons": reasons,
                    "last_error": "",
                },
            )
            _log_etl_event(
                "etl_success",
                user_id=user_id,
                conversation_id=conversation_id,
                run_id=run_id,
                reasons=reasons,
                attempt=attempt,
            )
            return last_result
        if last_result.get("skipped"):
            return last_result

    fail_time = _utc_now_iso()
    last_error = str(last_result.get("error") or "Fallo desconocido en ETL.")
    _update_etl_state(
        user_id,
        conversation_id,
        {
            "last_status": "failed",
            "attempts": len(backoff_seconds),
            "last_attempt_at": fail_time,
            "last_run_id": run_id,
            "last_reasons": reasons,
            "last_error": last_error,
        },
    )
    _log_etl_event(
        "etl_failed",
        user_id=user_id,
        conversation_id=conversation_id,
        run_id=run_id,
        reasons=reasons,
        attempt=len(backoff_seconds),
        error=last_error,
    )
    return last_result


def _worker_for_conversation(queue_key: str) -> None:
    while True:
        with _REGISTRY_LOCK:
            queue = _CONVERSATION_QUEUES.get(queue_key)
            if not queue:
                _ACTIVE_WORKERS.discard(queue_key)
                return
            task = queue.popleft() if len(queue) > 0 else None
            if task is None:
                _ACTIVE_WORKERS.discard(queue_key)
                _CONVERSATION_QUEUES.pop(queue_key, None)
                return

            if len(queue) == 0:
                _CONVERSATION_QUEUES.pop(queue_key, None)

        try:
            _execute_task_with_retries(task)
        except Exception as e:
            user_id = task.get("user_id", "")
            conversation_id = task.get("conversation_id", "")
            run_id = task.get("run_id", "")
            reasons = list(task.get("reasons") or [])
            error_msg = str(e)
            _update_etl_state(
                user_id,
                conversation_id,
                {
                    "last_status": "failed",
                    "last_run_id": run_id,
                    "last_reasons": reasons,
                    "last_error": error_msg,
                    "last_attempt_at": _utc_now_iso(),
                },
            )
            _log_etl_event(
                "etl_failed",
                user_id=user_id,
                conversation_id=conversation_id,
                run_id=run_id,
                reasons=reasons,
                attempt=0,
                error=error_msg,
            )


def enqueue_etl_run(
    user_id: str,
    conversation_id: str,
    jwt_token: Optional[str],
    reasons: List[str],
    run_id: str,
    django_api_url: Optional[str] = None,
) -> None:
    reasons = list(dict.fromkeys(reasons or []))
    _update_etl_state(
        user_id,
        conversation_id,
        {
            "last_status": "queued",
            "attempts": 0,
            "last_run_id": run_id,
            "last_reasons": reasons,
            "last_error": "",
        },
    )
    _log_etl_event(
        "etl_triggered",
        user_id=user_id,
        conversation_id=conversation_id,
        run_id=run_id,
        reasons=reasons,
    )

    task = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "jwt_token": jwt_token,
        "run_id": run_id,
        "reasons": reasons,
        "django_api_url": django_api_url,
    }
    dispatch_mode = _resolve_dispatch_mode()
    if dispatch_mode == "celery":
        try:
            _dispatch_via_celery(task)
            return
        except Exception as exc:
            logger.warning("Fallo al publicar ETL en Celery, uso fallback threading: %s", str(exc))

    _dispatch_via_threading(task)


def clear_inactivity_timer(user_id: str, conversation_id: str) -> None:
    key = _conversation_key(user_id, conversation_id)
    with _INACTIVITY_LOCK:
        timer = _INACTIVITY_TIMERS.pop(key, None)
    if timer:
        timer.cancel()


def schedule_inactivity_etl(
    user_id: str,
    conversation_id: str,
    jwt_token: Optional[str] = None,
    inactivity_seconds: Optional[int] = None,
) -> None:
    timeout_seconds = int(inactivity_seconds) if inactivity_seconds is not None else _DEFAULT_INACTIVITY_SECONDS
    timeout_seconds = max(1, timeout_seconds)
    key = _conversation_key(user_id, conversation_id)

    def _on_timeout() -> None:
        with _INACTIVITY_LOCK:
            current = _INACTIVITY_TIMERS.get(key)
            if current is not timer:
                return
            _INACTIVITY_TIMERS.pop(key, None)
        run_id = str(uuid.uuid4())
        reasons = ["inactivity_timeout"]
        try:
            enqueue_etl_run(
                user_id=user_id,
                conversation_id=conversation_id,
                jwt_token=jwt_token,
                reasons=reasons,
                run_id=run_id,
            )
        except Exception as e:
            _log_etl_event(
                "etl_failed",
                user_id=user_id,
                conversation_id=conversation_id,
                run_id=run_id,
                reasons=reasons,
                attempt=0,
                error=str(e),
            )

    timer = threading.Timer(timeout_seconds, _on_timeout)
    timer.daemon = True
    with _INACTIVITY_LOCK:
        previous = _INACTIVITY_TIMERS.get(key)
        if previous:
            previous.cancel()
        _INACTIVITY_TIMERS[key] = timer
    timer.start()
