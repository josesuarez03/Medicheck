import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.comprehend_medical import detect_entities


class ComprehendMedicalTests(unittest.TestCase):
    def test_extracts_pain_duration_and_symptoms(self):
        result = detect_entities("Tengo dolor de pecho 8/10 desde hace 2 horas y dificultad para respirar")
        summary = result["facts_summary"]
        self.assertEqual(summary["pain_scale"], 8)
        self.assertTrue(summary["duration"])
        self.assertTrue(summary["red_flags"])

    def test_negated_allergies_fact_present(self):
        result = detect_entities("No tengo alergias conocidas")
        allergy_facts = [fact for fact in result["facts"] if fact["category"] == "ALLERGY"]
        self.assertTrue(allergy_facts)
        self.assertTrue(any(fact["negated"] for fact in allergy_facts))

    def test_history_and_medications_detected(self):
        result = detect_entities("Tengo asma y estoy tomando paracetamol")
        categories = {fact["category"] for fact in result["facts"]}
        self.assertIn("MEDICAL_HISTORY", categories)
        self.assertIn("MEDICATION", categories)

    def test_greeting_discarded(self):
        result = detect_entities("hola")
        self.assertIn("hola", [segment.lower() for segment in result["discarded_segments"]])


if __name__ == "__main__":
    unittest.main()
