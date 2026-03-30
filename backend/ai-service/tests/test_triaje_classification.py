import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.medical_facts import FactsSummary
from services.triaje_classification import TriageClassification


class TriageClassificationTests(unittest.TestCase):
    def test_chest_pain_with_dyspnea_is_severe(self):
        summary = FactsSummary(chief_complaints=["dolor de pecho"], symptoms=["dolor torácico", "disnea"], red_flags=["dificultad para respirar"], pain_scale=8)
        triage = TriageClassification.from_facts(summary)
        self.assertEqual(triage.triage_level, "Severo")

    def test_mild_headache_is_mild(self):
        summary = FactsSummary(symptoms=["dolor de cabeza"], pain_scale=2)
        triage = TriageClassification.from_facts(summary)
        self.assertEqual(triage.triage_level, "Leve")

    def test_pain_and_functional_impact_is_moderate(self):
        summary = FactsSummary(symptoms=["dolor lumbar"], pain_scale=7, functional_impact=["no puedo trabajar"], duration="desde ayer")
        triage = TriageClassification.from_facts(summary)
        self.assertEqual(triage.triage_level, "Moderado")


if __name__ == "__main__":
    unittest.main()
