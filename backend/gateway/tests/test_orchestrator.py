import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

fake_etl_dispatcher = types.ModuleType("services.etl_dispatcher")
fake_etl_dispatcher.enqueue_etl_dispatch = lambda **kwargs: {"status": "queued", "task_id": "task-1", "run_id": "run-1"}
sys.modules.setdefault("services.etl_dispatcher", fake_etl_dispatcher)

from services.orchestrator import orchestrate_chat


class OrchestratorTests(unittest.TestCase):
    def test_dispatches_etl_when_ai_requests_closure(self):
        async def run():
            with patch(
                "services.orchestrator.forward_to_expert",
                return_value={"emergency_triggered": False, "triage_level": "Leve"},
            ), patch(
                "services.orchestrator.forward_to_ai",
                return_value={
                    "response": "Perfecto. Cierro esta consulta.",
                    "triaje_level": "Leve",
                    "conversation_state": {
                        "should_trigger_etl": True,
                        "etl_reason": "closure_confirmed",
                    },
                },
            ), patch("services.orchestrator.enqueue_etl_dispatch") as enqueue:
                enqueue.return_value = {"status": "queued", "task_id": "task-1", "run_id": "run-1"}
                result = await orchestrate_chat({"message": "ok gracias", "user_id": "user-1", "conversation_id": "conv-1"})
                self.assertEqual(result["etl_dispatch"]["status"], "queued")
                enqueue.assert_called_once()

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
