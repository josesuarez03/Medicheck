import asyncio
import json
import os
import time
import uuid
from contextlib import suppress

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from middleware.auth import decode_access_token
from services.etl_dispatcher import enqueue_etl_dispatch
from services.orchestrator import orchestrate_chat
from services.ws_session import WebSocketSessionStore


router = APIRouter(tags=["websocket"])

WS_AUTH_TIMEOUT_SECONDS = int(os.getenv("WS_AUTH_TIMEOUT_SECONDS", "10"))
WS_WARNING_SECONDS = max(30, int(os.getenv("WS_WARNING_SECONDS", "180")))
WS_INACTIVITY_TIMEOUT_SECONDS = max(WS_WARNING_SECONDS + 30, int(os.getenv("WS_INACTIVITY_TIMEOUT_SECONDS", "900")))


async def _send_json(websocket: WebSocket, payload: dict) -> None:
    await websocket.send_json(payload)


async def _close_if_unauthenticated(websocket: WebSocket, store: WebSocketSessionStore, connection_id: str) -> None:
    await asyncio.sleep(WS_AUTH_TIMEOUT_SECONDS)
    session = store.get_session(connection_id)
    if session.get("authenticated") is True:
        return
    await _send_json(
        websocket,
        {
            "event": "auth_timeout",
            "status": "error",
            "detail": "No se recibió autenticación en los primeros 10 segundos.",
        },
    )
    await websocket.close(code=1008)


async def _inactivity_watchdog(websocket: WebSocket, store: WebSocketSessionStore, connection_id: str) -> None:
    warning_sent = False
    while True:
        await asyncio.sleep(1)
        session = store.get_session(connection_id)
        if not session:
            return
        if session.get("authenticated") is not True:
            warning_sent = False
            continue
        last_activity_at = int(session.get("last_activity_at") or time.time())
        elapsed = time.time() - last_activity_at
        seconds_left = int(max(0, WS_INACTIVITY_TIMEOUT_SECONDS - elapsed))

        if seconds_left <= WS_WARNING_SECONDS and not warning_sent:
            warning_sent = True
            await _send_json(
                websocket,
                {
                    "event": "session_warning",
                    "status": "warning",
                    "seconds_left": seconds_left,
                    "message": "Se cerrará en 3 min por inactividad. ¿Algo más que añadir?",
                },
            )

        if seconds_left > WS_WARNING_SECONDS:
            warning_sent = False

        if seconds_left <= 0:
            user_id = str(session.get("user_id") or "")
            conversation_id = str(session.get("last_conversation_id") or "")
            jwt_token = str(session.get("jwt_token") or "") or None
            etl_dispatch = None
            if user_id and conversation_id:
                etl_dispatch = enqueue_etl_dispatch(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    jwt_token=jwt_token,
                    reasons=["inactivity_timeout"],
                )
            await _send_json(
                websocket,
                {
                    "event": "session_timeout",
                    "status": "timeout",
                    "seconds_left": 0,
                    "message": "La sesión se ha cerrado por inactividad.",
                    "etl_dispatch": etl_dispatch,
                },
            )
            await websocket.close(code=1001)
            return


def _resolve_user_id(payload: dict) -> str:
    return str(payload.get("user_id") or payload.get("sub") or "").strip()


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    store = WebSocketSessionStore()
    connection_id = str(uuid.uuid4())
    store.create_pending_session(connection_id=connection_id, client_host=getattr(websocket.client, "host", None))
    auth_timeout_task = asyncio.create_task(_close_if_unauthenticated(websocket, store, connection_id))
    inactivity_task = asyncio.create_task(_inactivity_watchdog(websocket, store, connection_id))
    await _send_json(
        websocket,
        {
            "event": "connection_pending",
            "status": "connected",
            "service": "gateway",
            "connection_id": connection_id,
            "message": "Conexión abierta. Envía el primer mensaje de autenticación.",
        },
    )
    try:
        while True:
            raw_payload = await websocket.receive_text()
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                await _send_json(websocket, {"event": "error", "status": "error", "detail": "Payload JSON inválido."})
                continue

            message_type = payload.get("type")
            if message_type in {"auth", "authenticate"}:
                token = str(payload.get("token") or "").strip()
                try:
                    auth_payload = decode_access_token(token)
                except HTTPException:
                    await _send_json(websocket, {"event": "auth_error", "status": "error", "detail": "Token inválido."})
                    continue
                user_id = _resolve_user_id(auth_payload)
                if not user_id:
                    await _send_json(websocket, {"event": "auth_error", "status": "error", "detail": "Token sin identificador de usuario."})
                    continue
                store.mark_authenticated(connection_id=connection_id, user_id=user_id, jwt_token=token)
                await _send_json(
                    websocket,
                    {
                        "event": "connection_success",
                        "status": "authenticated",
                        "user_id": user_id,
                        "connection_id": connection_id,
                    },
                )
                continue

            session = store.get_session(connection_id)
            if session.get("authenticated") is not True:
                await _send_json(
                    websocket,
                    {
                        "event": "auth_required",
                        "status": "error",
                        "detail": "Debes autenticar el socket antes de enviar mensajes.",
                    },
                )
                continue

            identity = str(session.get("user_id") or connection_id)
            if not store.check_rate_limit(identity=identity):
                await _send_json(
                    websocket,
                    {
                        "event": "rate_limit_exceeded",
                        "status": "error",
                        "detail": "Rate limit excedido para esta sesión.",
                    },
                )
                continue

            if message_type != "chat":
                await _send_json(websocket, {"event": "error", "status": "error", "detail": "Tipo de mensaje no soportado."})
                continue

            result = await orchestrate_chat(
                {
                    "message": payload.get("message", ""),
                    "context": payload.get("context", {}),
                    "user_data": payload.get("user_data", {}),
                    "conversation_id": payload.get("conversation_id"),
                    "user_id": session.get("user_id"),
                    "jwt_token": session.get("jwt_token"),
                }
            )
            conversation_id = result.get("conversation_id") or payload.get("conversation_id")
            store.update_activity(connection_id=connection_id, conversation_id=str(conversation_id or ""))
            await _send_json(
                websocket,
                {
                    "event": "chat_response",
                    "status": "ok",
                    "user_message": payload.get("message", ""),
                    **result,
                },
            )
    except WebSocketDisconnect:
        return
    finally:
        auth_timeout_task.cancel()
        inactivity_task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await auth_timeout_task
        with suppress(asyncio.CancelledError, Exception):
            await inactivity_task
        store.delete_session(connection_id)
