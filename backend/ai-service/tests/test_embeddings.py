import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.comprehend_medical import detect_entities
from services.embeddings import build_embedding_payload
from services.input_validate import analyze_message
from services.medical_facts import FactsSummary, MedicalFact


class EmbeddingsTests(unittest.TestCase):
    def test_greeting_skips_embedding(self):
        analysis = analyze_message("hola")
        payload = build_embedding_payload("hola", [], analysis, FactsSummary())
        self.assertTrue(payload.skipped)

    def test_clinical_payload_is_structured(self):
        extraction = detect_entities("Tengo dolor de pecho 8/10 desde hace 2 horas y disnea")
        facts = [MedicalFact(**fact) for fact in extraction["facts"]]
        summary = FactsSummary(**extraction["facts_summary"])
        analysis = analyze_message("Tengo dolor de pecho 8/10 desde hace 2 horas y disnea")
        payload = build_embedding_payload("Tengo dolor de pecho 8/10 desde hace 2 horas y disnea", facts, analysis, summary)
        self.assertFalse(payload.skipped)
        self.assertIn("motivo_consulta:", payload.embedding_text)
        self.assertIn("duracion:", payload.embedding_text)

    def test_single_clinical_entity_can_embed(self):
        extraction = detect_entities("Fiebre")
        facts = [MedicalFact(**fact) for fact in extraction["facts"]]
        summary = FactsSummary(**extraction["facts_summary"])
        analysis = analyze_message("Fiebre")
        payload = build_embedding_payload("Fiebre", facts, analysis, summary)
        self.assertFalse(payload.skipped)


if __name__ == "__main__":
    unittest.main()
