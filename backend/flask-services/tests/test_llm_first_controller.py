import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch


CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from routes import utils as route_utils  # noqa: E402
from services.chatbot.context_manager import PAIN_SCALE_QUESTION  # noqa: E402


def _fake_state(**kwargs):
    base = {
        "active_case_id": "headache_case",
        "active_node_id": "headache_q1",
        "required_fields_status": {"duration": False},
        "confidence": 0.9,
        "last_rule_ids": ["headache_rule_duration"],
        "fallback_reason": None,
        "emergency_triggered": False,
        "collected_fields": {},
        "triage_level": "Leve",
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _fake_decision(**kwargs):
    base = {
        "action": "ask",
        "response": "¿Desde cuándo tienes este dolor de cabeza?",
        "case_id": "headache_case",
        "confidence": 0.9,
        "rule_ids_applied": ["headache_rule_duration"],
        "fallback_reason": None,
        "emergency_triggered": False,
        "method_trace": ["rules", "tree", "scoring"],
        "triage_level": "Leve",
        "pain_scale": 0,
        "symptoms": ["dolor de cabeza"],
        "state": _fake_state(),
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


class LlmFirstControllerTests(unittest.TestCase):
    def test_expert_primary_when_case_matches(self):
        fake_decision = _fake_decision()
        llm_payload = {
            "context": {},
            "triaje_level": "Leve",
            "entities": [],
            "response": "Gracias por la información.",
            "symptoms": ["cefalea"],
            "symptoms_pattern": {},
            "pain_scale": 0,
            "missing_questions": [],
            "analysis_type": "general_response",
            "conversation_state": {
                "next_intent": "collect_missing_data",
                "questions_selected": ["¿Se acompaña de náuseas o mareo?"],
            },
        }
        with patch.object(route_utils.expert_orchestrator, "evaluate", return_value=fake_decision), patch.object(
            route_utils.fallback_model_adapter, "respond", return_value=llm_payload
        ), patch.object(route_utils.conversational_dataset_manager, "get_conversation", return_value=None), patch.object(
            route_utils.conversational_dataset_manager, "add_conversation", return_value="conv-llm-1"
        ), patch.object(
            route_utils.conversation_context_service, "append_turn", return_value=None
        ), patch(
            "routes.utils.schedule_inactivity_etl", return_value=None
        ):
            payload, status_code = route_utils.process_message_logic(
                user_id="user-1",
                user_message="Tengo dolor de cabeza",
                user_data={},
                conversation_id=None,
                jwt_token=None,
            )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["decision_flags"]["owner"], "expert_primary")
        self.assertFalse(payload["decision_flags"]["expert_guard_applied"])
        self.assertEqual(payload["response_source"], "expert")
        self.assertIn("¿Desde cuándo tienes este dolor de cabeza?", payload["conversation_state"]["questions_selected"])

    def test_emergency_combined_owner(self):
        fake_decision = _fake_decision(
            action="escalate",
            response="Debes acudir a urgencias de inmediato.",
            emergency_triggered=True,
            triage_level="Severo",
            state=_fake_state(
                active_node_id=None,
                required_fields_status={},
                emergency_triggered=True,
                triage_level="Severo",
            ),
        )
        llm_payload = {
            "context": {},
            "triaje_level": "Moderado",
            "entities": [],
            "response": "Podrías monitorizarte en casa.",
            "symptoms": [],
            "symptoms_pattern": {},
            "pain_scale": 0,
            "missing_questions": [],
            "analysis_type": "general_response",
            "conversation_state": {
                "next_intent": "collect_missing_data",
                "questions_selected": [],
            },
        }
        with patch.object(route_utils.expert_orchestrator, "evaluate", return_value=fake_decision), patch.object(
            route_utils.fallback_model_adapter, "respond", return_value=llm_payload
        ), patch.object(route_utils.conversational_dataset_manager, "get_conversation", return_value=None), patch.object(
            route_utils.conversational_dataset_manager, "add_conversation", return_value="conv-em-1"
        ), patch.object(
            route_utils.conversation_context_service, "append_turn", return_value=None
        ), patch(
            "routes.utils.enqueue_etl_run", return_value=None
        ):
            payload, status_code = route_utils.process_message_logic(
                user_id="user-1",
                user_message="Me falta mucho el aire y me desmayo.",
                user_data={},
                conversation_id=None,
                jwt_token=None,
            )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["decision_flags"]["owner"], "combined_emergency")
        self.assertEqual(payload["response_source"], "hybrid")
        self.assertEqual(payload["triaje_level"], "Severo")
        self.assertIn("Orientación adicional", payload["ai_response"])

    def test_forces_pain_question_by_second_turn(self):
        fake_decision = _fake_decision(
            action="fallback_ai",
            case_id=None,
            response="",
            state=_fake_state(
                active_case_id=None,
                active_node_id=None,
                required_fields_status={},
                fallback_reason="no_case_match",
            ),
        )
        llm_payload = {
            "context": {},
            "triaje_level": "Leve",
            "entities": [],
            "response": "Gracias por el detalle.",
            "symptoms": [],
            "symptoms_pattern": {},
            "pain_scale": 0,
            "missing_questions": [],
            "analysis_type": "general_response",
            "conversation_state": {
                "next_intent": "collect_missing_data",
                "questions_selected": ["¿Desde cuándo tienes este síntoma?"],
            },
        }
        current_conversation = {
            "_id": "conv-2",
            "messages": [
                {"role": "user", "content": "Me molesta la rodilla"},
                {"role": "assistant", "content": "¿Desde cuándo te molesta?"},
            ],
            "medical_context": {"context_snapshot": {}},
        }
        with patch.object(route_utils.expert_orchestrator, "evaluate", return_value=fake_decision), patch.object(
            route_utils.fallback_model_adapter, "respond", return_value=llm_payload
        ), patch.object(route_utils.conversational_dataset_manager, "get_conversation", return_value=current_conversation), patch.object(
            route_utils.conversational_dataset_manager, "update_conversation", return_value=None
        ), patch.object(
            route_utils.conversation_context_service, "append_turn", return_value=None
        ), patch(
            "routes.utils.schedule_inactivity_etl", return_value=None
        ):
            payload, status_code = route_utils.process_message_logic(
                user_id="user-1",
                user_message="Me sigue molestando al correr",
                user_data={},
                conversation_id="conv-2",
                jwt_token=None,
            )

        self.assertEqual(status_code, 200)
        self.assertTrue(payload["decision_flags"]["pain"]["must_ask"])
        self.assertTrue(payload["decision_flags"]["pain"]["asked_now"])
        self.assertIn(PAIN_SCALE_QUESTION, payload["conversation_state"]["questions_selected"])
        self.assertIsNone(payload["context"].get("pain_level_reported"))

    def test_expert_primary_when_llm_fails_but_case_matches(self):
        fake_decision = _fake_decision()
        with patch.object(route_utils.expert_orchestrator, "evaluate", return_value=fake_decision), patch.object(
            route_utils.fallback_model_adapter, "respond", return_value=None
        ), patch.object(route_utils.conversational_dataset_manager, "get_conversation", return_value=None), patch.object(
            route_utils.conversational_dataset_manager, "add_conversation", return_value="conv-exp-1"
        ), patch.object(
            route_utils.conversation_context_service, "append_turn", return_value=None
        ), patch(
            "routes.utils.schedule_inactivity_etl", return_value=None
        ):
            payload, status_code = route_utils.process_message_logic(
                user_id="user-1",
                user_message="Tengo dolor de cabeza",
                user_data={},
                conversation_id=None,
                jwt_token=None,
            )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["decision_flags"]["owner"], "expert_primary")
        self.assertEqual(payload["response_source"], "expert")
        self.assertIn("expert_confident_case_match", payload["decision_flags"]["reasons"])

    def test_reasks_previous_question_when_user_only_asks_to_continue(self):
        fake_decision = _fake_decision(
            action="fallback_ai",
            case_id=None,
            response="",
            state=_fake_state(
                active_case_id=None,
                active_node_id=None,
                required_fields_status={},
                fallback_reason="no_case_match",
            ),
        )
        llm_payload = {
            "context": {},
            "triaje_level": "Leve",
            "entities": [],
            "response": "",
            "symptoms": [],
            "symptoms_pattern": {},
            "pain_scale": 0,
            "missing_questions": [],
            "analysis_type": "general_response",
            "conversation_state": {
                "next_intent": "collect_missing_data",
                "questions_selected": [],
            },
        }
        current_conversation = {
            "_id": "conv-3",
            "messages": [
                {"role": "user", "content": "Tengo la nariz tapada"},
                {"role": "assistant", "content": PAIN_SCALE_QUESTION},
                {"role": "user", "content": "7"},
                {"role": "assistant", "content": "Gracias por la información."},
            ],
            "medical_context": {"context_snapshot": {}},
        }
        with patch.object(route_utils.expert_orchestrator, "evaluate", return_value=fake_decision), patch.object(
            route_utils.fallback_model_adapter, "respond", return_value=llm_payload
        ), patch.object(route_utils.conversational_dataset_manager, "get_conversation", return_value=current_conversation), patch.object(
            route_utils.conversational_dataset_manager, "update_conversation", return_value=None
        ), patch.object(
            route_utils.conversation_context_service, "append_turn", return_value=None
        ), patch(
            "routes.utils.schedule_inactivity_etl", return_value=None
        ):
            payload, status_code = route_utils.process_message_logic(
                user_id="user-1",
                user_message="cual es la siguiente pregunta",
                user_data={},
                conversation_id="conv-3",
                jwt_token=None,
            )

        self.assertEqual(status_code, 200)
        self.assertIn("Para continuar, necesito que respondas a esta pregunta:", payload["ai_response"])
        self.assertIn(PAIN_SCALE_QUESTION, payload["ai_response"])


if __name__ == "__main__":
    unittest.main()
