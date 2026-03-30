import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.bedrock_claude import TARGET_MAX_INPUT_TOKENS, build_turn_prompt


class BedrockPromptBudgetTests(unittest.TestCase):
    def test_prompt_stays_within_budget(self):
        bundle = {
            "user_input": "Tengo dolor de pecho desde hace 2 horas",
            "facts_summary": {"chief_complaints": ["dolor de pecho"], "symptoms": ["disnea"], "pain_scale": 8, "duration": "desde hace 2 horas", "red_flags": ["dificultad para respirar"]},
            "postgres_context": {"allergies": "penicilina", "medications": "ibuprofeno"},
            "recent_turns": [{"user_message": "hola", "assistant_message": "cuéntame el síntoma principal"}],
            "semantic_context": [{"text": "motivo: dolor torácico | dolor: 8/10"} for _ in range(5)],
            "global_semantic_context": [{"text": "antecedentes: ansiedad"} for _ in range(5)],
            "questions_selected": ["¿Cuánto tiempo llevas así?", "¿Tienes dificultad para respirar?"],
        }
        prompt = build_turn_prompt(bundle)
        self.assertLessEqual(prompt["prompt_token_budget"]["used_estimate"], TARGET_MAX_INPUT_TOKENS)
        self.assertIn("turn_input", prompt["prompt_sections_used"])


if __name__ == "__main__":
    unittest.main()
