import unittest
from pathlib import Path
import sys
import types
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

fake_data_connect = types.ModuleType("data.connect")
fake_data_connect.worker_redis_client = MagicMock()
sys.modules.setdefault("data.connect", fake_data_connect)

fake_models_conversation = types.ModuleType("models.conversation")


class _FakeConversationManager:
    def update_conversation_etl_state(self, *args, **kwargs):
        return None


fake_models_conversation.ConversationalDatasetManager = _FakeConversationManager
sys.modules.setdefault("models.conversation", fake_models_conversation)

fake_medical_data = types.ModuleType("services.medical_data")


class _FakeMedicalDataProcessor:
    def __init__(self, *args, **kwargs):
        pass

    def process_medical_data(self, *args, **kwargs):
        return {"triaje_level": "Leve"}


fake_medical_data.MedicalDataProcessor = _FakeMedicalDataProcessor
sys.modules.setdefault("services.medical_data", fake_medical_data)

fake_send_api = types.ModuleType("services.send_api")
fake_send_api.send_data_to_django = lambda *args, **kwargs: {"status": "ok"}
sys.modules.setdefault("services.send_api", fake_send_api)

from services import etl_runner


class EtlRunnerTests(unittest.TestCase):
    def test_enqueue_etl_run_uses_celery_when_enabled(self):
        with patch.object(etl_runner.Config, "ETL_DISPATCH_MODE", "celery"), patch.object(
            etl_runner, "_update_etl_state"
        ), patch.object(etl_runner, "_log_etl_event"), patch.object(
            etl_runner, "_dispatch_via_celery"
        ) as dispatch_celery, patch.object(
            etl_runner, "_dispatch_via_threading"
        ) as dispatch_threading:
            etl_runner.enqueue_etl_run(
                user_id="user-1",
                conversation_id="conv-1",
                jwt_token="jwt",
                reasons=["new_signal"],
                run_id="run-1",
            )

        dispatch_celery.assert_called_once()
        dispatch_threading.assert_not_called()

    def test_enqueue_etl_run_falls_back_to_threading_when_celery_publish_fails(self):
        with patch.object(etl_runner.Config, "ETL_DISPATCH_MODE", "celery"), patch.object(
            etl_runner, "_update_etl_state"
        ), patch.object(etl_runner, "_log_etl_event"), patch.object(
            etl_runner, "_dispatch_via_celery", side_effect=RuntimeError("broker down")
        ), patch.object(etl_runner, "_dispatch_via_threading") as dispatch_threading:
            etl_runner.enqueue_etl_run(
                user_id="user-1",
                conversation_id="conv-1",
                jwt_token=None,
                reasons=["inactivity_timeout"],
                run_id="run-2",
            )

        dispatch_threading.assert_called_once()

    def test_execute_etl_once_skips_when_lock_is_already_held(self):
        with patch.object(etl_runner, "_acquire_etl_lock", return_value=False), patch.object(
            etl_runner, "_log_etl_event"
        ):
            result = etl_runner.execute_etl_once(
                user_id="user-1",
                conversation_id="conv-1",
                run_id="run-3",
                reasons=["new_signal"],
            )

        self.assertFalse(result["success"])
        self.assertTrue(result["skipped"])
        self.assertIn("ya en ejecución", result["error"])

    def test_execute_etl_once_releases_lock_after_success(self):
        processor = MagicMock()
        processor.process_medical_data.return_value = {"triaje_level": "Leve"}

        with patch.object(etl_runner, "_acquire_etl_lock", return_value=True), patch.object(
            etl_runner, "_release_etl_lock"
        ) as release_lock, patch.object(
            etl_runner, "MedicalDataProcessor", return_value=processor
        ), patch.object(
            etl_runner, "send_data_to_django", return_value={"status": "ok"}
        ):
            result = etl_runner.execute_etl_once(
                user_id="user-1",
                conversation_id="conv-1",
                jwt_token="jwt",
                run_id="run-4",
                reasons=["new_signal"],
            )

        self.assertTrue(result["success"])
        release_lock.assert_called_once_with("user-1", "conv-1", "run-4")


if __name__ == "__main__":
    unittest.main()
