import asyncio
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import WebSocketDisconnect
from starlette.websockets import WebSocketState

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

fake_etl_dispatcher = types.ModuleType("services.etl_dispatcher")
fake_etl_dispatcher.enqueue_etl_dispatch = lambda **kwargs: {"status": "queued", "task_id": "task-1", "run_id": "run-1"}
fake_etl_dispatcher.schedule_inactivity_etl = lambda **kwargs: {"status": "scheduled", "task_id": "task-2", "run_id": "run-2"}
fake_etl_dispatcher.clear_inactivity_token = lambda **kwargs: None
sys.modules.setdefault("services.etl_dispatcher", fake_etl_dispatcher)

from routers import ws_router


class FakeWebSocket:
    def __init__(self, incoming_messages):
        self._incoming_messages = list(incoming_messages)
        self.sent_messages = []
        self.closed = False
        self.client = types.SimpleNamespace(host="127.0.0.1")
        self.application_state = WebSocketState.CONNECTED

    async def accept(self):
        return None

    async def receive_text(self):
        if self._incoming_messages:
            return self._incoming_messages.pop(0)
        raise WebSocketDisconnect()

    async def send_json(self, payload):
        self.sent_messages.append(payload)

    async def close(self, code=1000):
        self.closed = True
        self.close_code = code
        self.application_state = WebSocketState.DISCONNECTED


class DisconnectOnFirstSendWebSocket(FakeWebSocket):
    async def send_json(self, payload):
        self.application_state = WebSocketState.DISCONNECTED
        raise WebSocketDisconnect(code=1006)


class WebSocketRouterTests(unittest.TestCase):
    def test_disconnect_during_initial_pending_message_is_swallowed(self):
        websocket = DisconnectOnFirstSendWebSocket([])

        async def run():
            await ws_router.chat_ws(websocket)

        asyncio.run(run())
        self.assertFalse(websocket.closed)

    def test_requires_authentication_before_chat(self):
        websocket = FakeWebSocket([json.dumps({"type": "chat", "message": "hola"})])

        async def run():
            await ws_router.chat_ws(websocket)

        asyncio.run(run())
        self.assertEqual(websocket.sent_messages[0]["event"], "connection_pending")
        self.assertEqual(websocket.sent_messages[1]["event"], "auth_required")

    def test_authenticates_in_first_message_and_forwards_chat(self):
        websocket = FakeWebSocket(
            [
                json.dumps({"type": "authenticate", "token": "jwt-token"}),
                json.dumps({"type": "chat", "message": "hola", "conversation_id": "conv-1"}),
            ]
        )

        async def run():
            with patch("routers.ws_router.decode_access_token", return_value={"sub": "user-1", "raw_token": "jwt-token"}), patch(
                "routers.ws_router.orchestrate_chat",
                return_value={
                    "status": "ok",
                    "service": "gateway",
                    "conversation_id": "conv-1",
                    "response": "respuesta",
                    "triaje_level": "Leve",
                },
            ):
                await ws_router.chat_ws(websocket)

        asyncio.run(run())
        self.assertEqual(websocket.sent_messages[0]["event"], "connection_pending")
        self.assertEqual(websocket.sent_messages[1]["event"], "connection_success")
        self.assertEqual(websocket.sent_messages[2]["event"], "chat_response")
        self.assertEqual(websocket.sent_messages[2]["response"], "respuesta")
        self.assertEqual(websocket.sent_messages[2]["user_message"], "hola")

    def test_chat_orchestration_error_keeps_socket_alive_and_returns_error_event(self):
        websocket = FakeWebSocket(
            [
                json.dumps({"type": "authenticate", "token": "jwt-token"}),
                json.dumps({"type": "chat", "message": "hola"}),
            ]
        )

        async def run():
            with patch("routers.ws_router.decode_access_token", return_value={"sub": "user-1", "raw_token": "jwt-token"}), patch(
                "routers.ws_router.orchestrate_chat",
                side_effect=RuntimeError("La variable AI_SERVICE_URL debe incluir una URL absoluta con http:// o https://."),
            ):
                await ws_router.chat_ws(websocket)

        asyncio.run(run())
        self.assertEqual(websocket.sent_messages[0]["event"], "connection_pending")
        self.assertEqual(websocket.sent_messages[1]["event"], "connection_success")
        self.assertEqual(websocket.sent_messages[2]["event"], "chat_error")
        self.assertFalse(websocket.closed)


if __name__ == "__main__":
    unittest.main()
