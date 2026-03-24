import os
import sys
import unittest


CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from models.conversation import ConversationalDatasetManager  # noqa: E402


class _FakeEncryption:
    def __init__(self, mapping):
        self.mapping = mapping

    def decrypt_string(self, value):
        if value not in self.mapping:
            raise ValueError("unknown encrypted payload")
        return self.mapping[value]


class ConversationEncryptionCompatTests(unittest.TestCase):
    def test_decrypts_legacy_encrypted_strings_without_schema_version(self):
        manager = ConversationalDatasetManager.__new__(ConversationalDatasetManager)
        manager._encryption = lambda: _FakeEncryption(
            {
                "enc_messages": '[{"role":"user","content":"hola"}]',
                "enc_context": '{"context_snapshot":{"chief_complaint":"dolor de cabeza"}}',
            }
        )

        conversation = {
            "_id": "conv-1",
            "messages": "enc_messages",
            "medical_context": "enc_context",
        }

        decrypted = manager._decrypt_sensitive_fields(conversation)

        self.assertEqual(decrypted["messages"][0]["content"], "hola")
        self.assertEqual(
            decrypted["medical_context"]["context_snapshot"]["chief_complaint"],
            "dolor de cabeza",
        )

    def test_parses_plain_json_strings_when_payload_is_not_encrypted(self):
        manager = ConversationalDatasetManager.__new__(ConversationalDatasetManager)
        manager._encryption = lambda: _FakeEncryption({})

        conversation = {
            "_id": "conv-2",
            "messages": '[{"role":"assistant","content":"¿Desde cuándo?"}]',
            "medical_context": '{"context_snapshot":{"symptom_duration":"2 dias"}}',
        }

        decrypted = manager._decrypt_sensitive_fields(conversation)

        self.assertEqual(decrypted["messages"][0]["role"], "assistant")
        self.assertEqual(
            decrypted["medical_context"]["context_snapshot"]["symptom_duration"],
            "2 dias",
        )
