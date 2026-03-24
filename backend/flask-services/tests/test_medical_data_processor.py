import os
import sys
import types
import unittest
from unittest.mock import patch


CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Stub external dependencies so this test stays focused on normalization logic.
fake_conversation_module = types.ModuleType("models.conversation")


class _FakeConversationalDatasetManager:
    def get_conversation(self, *_args, **_kwargs):
        return None


fake_conversation_module.ConversationalDatasetManager = _FakeConversationalDatasetManager
sys.modules.setdefault("models.conversation", fake_conversation_module)

fake_comprehend_module = types.ModuleType("services.chatbot.comprehend_medical")
fake_comprehend_module.detect_entities = lambda *_args, **_kwargs: []
sys.modules.setdefault("services.chatbot.comprehend_medical", fake_comprehend_module)

fake_bedrock_module = types.ModuleType("services.chatbot.bedrock_claude")
fake_bedrock_module.call_claude = lambda *_args, **_kwargs: ""
sys.modules.setdefault("services.chatbot.bedrock_claude", fake_bedrock_module)

from services.api.send_api import _auth_headers, _sign_internal_payload  # noqa: E402
from services.process_data.medical_data import MedicalDataProcessor  # noqa: E402
from config.config import Config  # noqa: E402
from services.security.encryption import Encryption  # noqa: E402


class MedicalDataProcessorTests(unittest.TestCase):
    def test_extract_structured_data_normalizes_pain_scale_and_empty_triage(self):
        processor = MedicalDataProcessor()
        structured_data = processor.extract_structured_data(
            conversation={"pain_scale": "7.0", "triaje_level": ""},
            messages=[],
            enhanced_entities=[],
        )

        self.assertIsNone(structured_data["triaje_level"])
        self.assertEqual(structured_data["pain_scale"], 7)

    def test_extract_structured_data_drops_invalid_pain_scale(self):
        processor = MedicalDataProcessor()
        structured_data = processor.extract_structured_data(
            conversation={"pain_scale": "invalid", "triaje_level": "Moderado"},
            messages=[],
            enhanced_entities=[],
        )

        self.assertEqual(structured_data["triaje_level"], "Moderado")
        self.assertIsNone(structured_data["pain_scale"])

    def test_auth_headers_do_not_use_static_integration_token(self):
        headers = _auth_headers(jwt_token=None)
        self.assertNotIn("X-Django-Integration-Token", headers)

    def test_internal_payload_signing_uses_hmac_headers(self):
        payload = {"user_id": "user-1", "medical_data": {"pain_scale": 4}, "source": "chatbot"}
        original_key = Config.FLASK_API_KEY
        Config.FLASK_API_KEY = "test-secret"
        timestamp, signature = _sign_internal_payload(payload, timestamp=1234567890)
        Config.FLASK_API_KEY = original_key

        self.assertEqual(timestamp, "1234567890")
        self.assertEqual(len(signature), 64)

    def test_validate_fails_when_required_env_is_missing(self):
        original_password = Config.REDIS_PASSWORD
        with patch.dict(os.environ, {"REDIS_PASSWORD": ""}, clear=False):
            Config.REDIS_PASSWORD = ""
            with self.assertRaises(EnvironmentError):
                Config.validate()
        Config.REDIS_PASSWORD = original_password

    def test_validate_fails_when_mongo_encryption_key_is_invalid(self):
        original_key = Config.MONGO_ENCRYPTION_KEY
        with patch.dict(os.environ, {"MONGO_ENCRYPTION_KEY": "invalid-key"}, clear=False):
            Config.MONGO_ENCRYPTION_KEY = "invalid-key"
            with self.assertRaises(EnvironmentError):
                Config.validate()
        Config.MONGO_ENCRYPTION_KEY = original_key

    def test_encryption_requires_valid_fernet_key(self):
        with self.assertRaises(ValueError):
            Encryption(key="invalid-key")


if __name__ == "__main__":
    unittest.main()
