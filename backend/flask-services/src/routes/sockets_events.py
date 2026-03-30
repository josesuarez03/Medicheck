import logging
import uuid

from flask import request
from flask_socketio import emit, join_room, leave_room

from data.connect import context_redis_client
from services.auth.auth import get_user_id_from_token
from services.chatbot.application.chat_turn_service import process_message_logic
from services.process_data.etl_runner import clear_inactivity_timer, enqueue_etl_run

from . import socketio

logger = logging.getLogger(__name__)

AUTH_TTL_SECONDS = 60 * 15
CONVERSATION_TTL_SECONDS = 60 * 60
AUTH_DEADLINE_SECONDS = 5
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_MESSAGES = 20


def _auth_key(sid: str) -> str:
    return f"ws:auth:{sid}"


def _conversation_key(sid: str) -> str:
    return f"ws:conversation:{sid}"


def _rate_key(user_id: str) -> str:
    return f"ws:rate:{user_id}"


def _get_authenticated_user_id(sid: str) -> str | None:
    return context_redis_client.get(_auth_key(sid))


def _set_authenticated_user_id(sid: str, user_id: str) -> None:
    context_redis_client.setex(_auth_key(sid), AUTH_TTL_SECONDS, user_id)


def _get_active_conversation_id(sid: str) -> str | None:
    return context_redis_client.get(_conversation_key(sid))


def _set_active_conversation_id(sid: str, conversation_id: str) -> None:
    context_redis_client.setex(_conversation_key(sid), CONVERSATION_TTL_SECONDS, conversation_id)


def _clear_socket_state(sid: str) -> None:
    context_redis_client.delete(_auth_key(sid), _conversation_key(sid))


def _require_authenticated_user(sid: str) -> str | None:
    user_id = _get_authenticated_user_id(sid)
    if user_id:
        return user_id

    emit(
        "auth_required",
        {"error": "Autenticación requerida.", "error_code": "auth_required"},
        room=sid,
    )
    logger.warning("ws_auth_rejected sid=%s reason=missing_auth", sid)
    return None


def _check_rate_limit(user_id: str) -> bool:
    rate_key = _rate_key(user_id)
    current_count = context_redis_client.incr(rate_key)
    if current_count == 1:
        context_redis_client.expire(rate_key, RATE_LIMIT_WINDOW_SECONDS)
    return current_count <= RATE_LIMIT_MAX_MESSAGES


def _schedule_auth_deadline(sid: str) -> None:
    socketio.start_background_task(_enforce_auth_deadline, sid)


def _enforce_auth_deadline(sid: str) -> None:
    socketio.sleep(AUTH_DEADLINE_SECONDS)
    if _get_authenticated_user_id(sid):
        return
    logger.warning("ws_auth_rejected sid=%s reason=auth_timeout", sid)
    socketio.server.disconnect(sid, namespace="/")


@socketio.on("connect")
def handle_connect():
    sid = request.sid
    logger.info("Cliente conectado: %s", sid)
    emit("connection_success", {"status": "connected"}, room=sid)
    _schedule_auth_deadline(sid)


@socketio.on("authenticate")
def handle_authenticate(data):
    sid = request.sid
    if not isinstance(data, dict):
        emit("auth_required", {"error": "Payload de autenticación inválido.", "error_code": "auth_required"}, room=sid)
        return

    token = data.get("token")
    user_id = get_user_id_from_token(token)
    if not user_id:
        emit("auth_required", {"error": "Token inválido o expirado.", "error_code": "auth_required"}, room=sid)
        logger.warning("ws_auth_rejected sid=%s reason=invalid_token", sid)
        return

    _set_authenticated_user_id(sid, str(user_id))
    join_room(str(user_id))
    emit("authenticated", {"status": "authenticated", "user_id": str(user_id)}, room=sid)
    logger.info("Cliente %s autenticado como user_id %s", sid, user_id)


@socketio.on("disconnect")
def handle_disconnect(reason=None):
    sid = request.sid
    user_id = _get_authenticated_user_id(sid)
    conversation_id = _get_active_conversation_id(sid)
    if user_id and conversation_id:
        run_id = str(uuid.uuid4())
        try:
            clear_inactivity_timer(user_id, conversation_id)
            enqueue_etl_run(
                user_id=user_id,
                conversation_id=conversation_id,
                jwt_token=None,
                reasons=["websocket_disconnect"],
                run_id=run_id,
            )
            logger.info(
                "ETL encolada por disconnect sid=%s user=%s conversation=%s run_id=%s",
                sid,
                user_id,
                conversation_id,
                run_id,
            )
        except Exception as exc:
            logger.warning(
                "No se pudo encolar ETL por disconnect sid=%s user=%s conversation=%s: %s",
                sid,
                user_id,
                conversation_id,
                str(exc),
            )
    _clear_socket_state(sid)
    logger.info("Cliente desconectado: %s. Razón: %s", sid, reason)


@socketio.on("chat_message")
def handle_chat_message(data):
    sid = request.sid
    if not isinstance(data, dict):
        emit("error", {"error": "Formato de mensaje inválido."}, room=sid)
        return

    user_id = _require_authenticated_user(sid)
    if not user_id:
        return

    if not _check_rate_limit(user_id):
        emit(
            "error",
            {
                "error": "Demasiados mensajes, espera un momento.",
                "error_code": "rate_limited",
            },
            room=sid,
        )
        logger.warning("ws_rate_limited sid=%s user_id=%s", sid, user_id)
        return

    user_message = data.get("message", "")
    if not isinstance(user_message, str) or not user_message.strip():
        emit("error", {"error": "El mensaje no puede estar vacío."}, room=sid)
        return

    try:
        user_data = data.get("context", {})
        conversation_id = data.get("conversation_id")
        emit("typing", {"status": "bot is typing"}, room=sid)

        result, status_code = process_message_logic(
            user_id,
            user_message,
            user_data,
            conversation_id,
            jwt_token=None,
        )

        if status_code != 200:
            emit("error", result, room=sid)
            return

        result_conversation_id = result.get("conversation_id")
        if result_conversation_id:
            _set_active_conversation_id(sid, result_conversation_id)
        emit("chat_response", result, room=sid)
    except Exception as exc:
        logger.error("Error en WebSocket chat_message para SID %s: %s", sid, str(exc), exc_info=True)
        emit("error", {"error": "Error interno del servidor."}, room=sid)


@socketio.on("join_conversation")
def on_join_conversation(data):
    sid = request.sid
    user_id = _require_authenticated_user(sid)
    if not user_id:
        return

    if not isinstance(data, dict):
        emit("error", {"error": "Formato de mensaje inválido."}, room=sid)
        return

    conversation_id = data.get("conversation_id")
    if not conversation_id:
        emit("error", {"error": "conversation_id es requerido."}, room=sid)
        return

    join_room(conversation_id)
    _set_active_conversation_id(sid, conversation_id)
    emit("room_joined", {"room": conversation_id, "status": "joined"}, room=sid)
    logger.info("Cliente %s se unió a la conversación %s", sid, conversation_id)


@socketio.on("leave_conversation")
def on_leave_conversation(data):
    sid = request.sid
    user_id = _require_authenticated_user(sid)
    if not user_id:
        return

    if not isinstance(data, dict):
        emit("error", {"error": "Formato de mensaje inválido."}, room=sid)
        return

    conversation_id = data.get("conversation_id")
    if not conversation_id:
        emit("error", {"error": "conversation_id es requerido."}, room=sid)
        return

    leave_room(conversation_id)
    context_redis_client.delete(_conversation_key(sid))
    etl_enqueued = False
    etl_run_id = ""
    try:
        etl_run_id = str(uuid.uuid4())
        clear_inactivity_timer(user_id, conversation_id)
        enqueue_etl_run(
            user_id=user_id,
            conversation_id=conversation_id,
            jwt_token=None,
            reasons=["websocket_room_closed"],
            run_id=etl_run_id,
        )
        etl_enqueued = True
    except Exception as exc:
        logger.warning(
            "No se pudo encolar ETL por cierre de room sid=%s user=%s conversation=%s: %s",
            sid,
            user_id,
            conversation_id,
            str(exc),
        )

    emit(
        "room_left",
        {
            "room": conversation_id,
            "status": "left",
            "etl_queued": etl_enqueued,
            "etl_run_id": etl_run_id,
        },
        room=sid,
    )


@socketio.on("sync_request")
def handle_sync_request(data):
    sid = request.sid
    user_id = _require_authenticated_user(sid)
    if not user_id:
        return

    if not isinstance(data, dict):
        emit("sync_error", {"error": "Formato de mensaje inválido."}, room=sid)
        return

    try:
        from services.chatbot.application.conversation_service import conversation_service

        conversation_id = data.get("conversation_id")
        conversation_service.sync_to_mongo(user_id, conversation_id)
        emit("sync_complete", {"success": True, "message": "Sincronización completada."}, room=sid)
    except Exception as exc:
        logger.error("Error en sincronización WebSocket para SID %s: %s", sid, str(exc), exc_info=True)
        emit("sync_error", {"error": "Error en la sincronización."}, room=sid)
