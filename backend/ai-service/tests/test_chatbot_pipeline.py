import pathlib
import sys
import unittest


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

    def test_low_signal_after_turn_does_not_embed(self):
        result = Chatbot("ok", {"patient_profile": {"name": "Ana"}}, existing_context={"chief_complaint": "dolor de cabeza"}).initialize_conversation()
        self.assertTrue(result["embedding_payload"]["skipped"])


if __name__ == "__main__":
    unittest.main()
