import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.input_validate import analyze_message


class InputValidateTests(unittest.TestCase):
    def test_greeting_has_low_signal(self):
        result = analyze_message("hola")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.analysis_type, "greeting")
        self.assertLess(result.clinical_signal_score, 0.15)

    def test_ok_is_non_clinical(self):
        result = analyze_message("ok")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.analysis_type, "non_clinical")

    def test_clinical_message_detected(self):
        result = analyze_message("Tengo dolor de pecho desde hace 2 horas")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.analysis_type, "clinical")

    def test_harmful_pattern_rejected(self):
        result = analyze_message("<script>alert(1)</script>")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.analysis_type, "input_error")

    def test_diagnosis_restriction_detected(self):
        result = analyze_message("¿Qué diagnóstico tengo?")
        self.assertEqual(result.analysis_type, "diagnosis_restriction")


if __name__ == "__main__":
    unittest.main()
