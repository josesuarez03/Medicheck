import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.orchestrator import orchestrate_chat


router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    authenticated_user_id = None
    await websocket.send_json({"status": "connected", "service": "gateway", "message": "Envía un mensaje JSON."})
    try:
        while True:
            raw_payload = await websocket.receive_text()
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                await websocket.send_json({"status": "error", "detail": "Payload JSON inválido."})
                continue

            if payload.get("type") == "auth":
                authenticated_user_id = payload.get("user_id")
                await websocket.send_json({"status": "authenticated", "user_id": authenticated_user_id})
                continue

            if payload.get("type") != "chat":
                await websocket.send_json({"status": "error", "detail": "Tipo de mensaje no soportado."})
                continue

            result = await orchestrate_chat(
                {
                    "message": payload.get("message", ""),
                    "context": payload.get("context", {}),
                    "user_data": payload.get("user_data", {}),
                    "conversation_id": payload.get("conversation_id"),
                    "user_id": authenticated_user_id,
                }
            )
            await websocket.send_json(result)
    except WebSocketDisconnect:
        return
