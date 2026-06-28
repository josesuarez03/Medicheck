import pathlib
import sys
import unittest
from unittest.mock import patch


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.chatbot import Chatbot


class ChatbotPipelineTests(unittest.TestCase):
    def test_greeting_does_not_trigger_deep_pipeline(self):
        result = Chatbot("hola", {}).initialize_conversation()
        self.assertEqual(result["analysis_type"], "greeting")
        self.assertTrue(result["embedding_payload"]["skipped"])

    def test_clinical_message_returns_structured_facts(self):
        result = Chatbot("Tengo dolor de pecho 8/10 desde hace 2 horas y disnea", {}).initialize_conversation()
        self.assertIn("structured_facts", result)
        self.assertTrue(result["facts_summary"]["red_flags"])
        self.assertIn("prompt_sections_used", result)
        self.assertEqual(result["retrieval"]["level"], "full")

    def test_low_signal_after_turn_does_not_embed(self):
        result = Chatbot("ok", {"patient_profile": {"name": "Ana"}}, existing_context={"chief_complaint": "dolor de cabeza"}).initialize_conversation()
        self.assertTrue(result["embedding_payload"]["skipped"])

    def test_clinical_message_returns_retrieval_metadata(self):
        result = Chatbot("Tengo fiebre y tos desde ayer", {}).initialize_conversation()
        self.assertIn("retrieval", result)
        self.assertIn(result["retrieval"]["level"], {"medium", "full"})

    def test_duplicate_closure_does_not_trigger_etl_for_same_context(self):
        chatbot = Chatbot(
            "ok gracias",
            {},
            existing_context={
                "awaiting_closure_confirmation": True,
                "facts_summary": {"chief_complaints": ["dolor de cabeza"], "symptoms": ["dolor de cabeza"]},
                "conversation_state": {},
                "hybrid_state": {"etl": {"last_status": "success"}},
                "last_triaje_level": "Leve",
            },
        )
        chatbot.existing_context["conversation_state"]["current_case_signature"] = chatbot._current_case_signature()

        result = chatbot.initialize_conversation()

        self.assertEqual(result["conversation_state"]["next_intent"], "etl_skipped_same_context")
        self.assertFalse(result["conversation_state"]["should_trigger_etl"])

    def test_first_turn_preserves_provided_conversation_id(self):
        class FakeConversationManager:
            def __init__(self):
                self.created_ids = []

            def get_conversation(self, user_id, conversation_id):
                return None

            def add_conversation(
                self,
                user_id,
                medical_context,
                messages,
                symptoms,
                symptoms_pattern,
                pain_scale,
                triaje_level,
                conversation_id=None,
            ):
                self.created_ids.append(conversation_id)
                return conversation_id

        fake_manager = FakeConversationManager()

        with patch("services.chatbot.ConversationalDatasetManager", return_value=fake_manager), patch(
            "services.chatbot.ConversationContextService",
            side_effect=RuntimeError("context store unavailable"),
        ):
            result = Chatbot(
                "Tengo dolor de pecho 8/10 desde hace 2 horas y disnea",
                {},
                user_id="user-1",
                conversation_id="conv-1",
            ).initialize_conversation()

        self.assertEqual(result["conversation_id"], "conv-1")
        self.assertEqual(fake_manager.created_ids, ["conv-1"])


if __name__ == "__main__":
    unittest.main()
