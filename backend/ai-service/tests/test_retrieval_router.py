import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.medical_facts import FactsSummary
from services.retrieval_router import RetrievalRouter


class RetrievalRouterTests(unittest.TestCase):
    def test_non_clinical_turn_uses_cheap_mode(self):
        decision = RetrievalRouter.decide(
            clinical_signal_score=0.05,
            facts_summary=FactsSummary(),
            triage_level="Leve",
            analysis_type="non_clinical",
            existing_context={},
        )
        self.assertEqual(decision.level, "cheap")

    def test_moderate_clinical_turn_uses_summary_and_one_memory(self):
        decision = RetrievalRouter.decide(
            clinical_signal_score=0.32,
            facts_summary=FactsSummary(symptoms=["fiebre"]),
            triage_level="Leve",
            analysis_type="clinical",
            existing_context={},
        )
        self.assertEqual(decision.level, "medium")
        self.assertTrue(decision.use_summary)
        self.assertEqual(decision.episodic_top_k, 1)

    def test_severe_turn_uses_full_rag(self):
        decision = RetrievalRouter.decide(
            clinical_signal_score=0.8,
            facts_summary=FactsSummary(red_flags=["disnea"], pain_scale=8),
            triage_level="Severo",
            analysis_type="clinical",
            existing_context={"known_allergies": "penicilina"},
        )
        self.assertEqual(decision.level, "full")
        self.assertEqual(decision.episodic_top_k, 2)
        self.assertEqual(decision.global_top_k, 2)
