import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.closure_intent import classify_closure_message


class ClosureIntentTests(unittest.TestCase):
    def test_ok_gracias_triggers_closure(self):
        with patch("services.closure_intent.detect_entities", return_value={"facts_summary": {}}):
            result = classify_closure_message("ok gracias")
        self.assertEqual(result.intent, "closure")
        self.assertTrue(result.should_trigger_etl)

    def test_new_clinical_symptom_keeps_session_open(self):
        with patch(
            "services.closure_intent.detect_entities",
            return_value={"facts_summary": {"chief_complaints": ["dolor de pecho"], "symptoms": ["dolor de pecho"]}},
        ):
            result = classify_closure_message("también me duele el pecho")
        self.assertEqual(result.intent, "clinical")
        self.assertTrue(result.should_continue_session)

    def test_question_after_triage_does_not_trigger_etl(self):
        with patch("services.closure_intent.detect_entities", return_value={"facts_summary": {}}):
            result = classify_closure_message("¿y eso es grave?")
        self.assertEqual(result.intent, "ambiguous_question")
        self.assertFalse(result.should_trigger_etl)

    def test_uncertain_followup_requests_explicit_confirmation(self):
        with patch("services.closure_intent.detect_entities", return_value={"facts_summary": {}}):
            result = classify_closure_message("mm no se")
        self.assertEqual(result.intent, "uncertain")
        self.assertTrue(result.should_ask_explicit_confirmation)


if __name__ == "__main__":
    unittest.main()
