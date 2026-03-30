from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(
        {
            "status": "connected",
            "service": "gateway",
            "message": "Scaffold FastAPI activo. La orquestacion WS aun no ha sido migrada desde Flask.",
        }
    )
    try:
        while True:
            payload = await websocket.receive_text()
            await websocket.send_json(
                {
                    "status": "pending",
                    "service": "gateway",
                    "echo": payload,
                }
            )
    except WebSocketDisconnect:
        return
