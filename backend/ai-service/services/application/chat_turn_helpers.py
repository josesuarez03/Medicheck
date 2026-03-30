import re
import unicodedata
from typing import Any, Dict, List, Tuple

from config.config import Config
from services.chatbot.context_manager import is_pain_scale_question

TRIAGE_RANK = {"LEVE": 1, "MODERADO": 2, "SEVERO": 3}
HYBRID_RESERVED_KEYS = {"analysis", "context_snapshot", "expert_state", "expert_trace", "hybrid_state"}
SAFETY_QUESTION_HINTS = ("dificultad para respirar", "dolor de pecho", "desmayo", "fiebre", "convuls")
EXPLICIT_CLOSE_PHRASES = (
    "eso es todo",
    "gracias termine",
    "termine",
    "fin",
    "cerrar chat",
    "hasta luego",
)
BOT_CLOSE_PHRASES = (
    "espero haberte ayudado",
    "si necesitas algo mas",
    "si necesitas algo más",
    "no dudes en volver",
    "consulta finalizada",
    "puedes volver cuando quieras",
    "quedo atento",
)


def _normalize_triage(level: str | None) -> str:
    value = str(level or "").strip().capitalize()
    if value in {"Leve", "Moderado", "Severo"}:
        return value
    return "Leve"


def _triage_rank(level: str | None) -> int:
    return TRIAGE_RANK.get(_normalize_triage(level).upper(), 1)


def _max_triage_level(level_a: str | None, level_b: str | None) -> str:
    a = _normalize_triage(level_a)
    b = _normalize_triage(level_b)
    return a if _triage_rank(a) >= _triage_rank(b) else b


def _safe_int_0_10(value: Any) -> int | None:
    return value if isinstance(value, int) and 0 <= value <= 10 else None


def _hydrate_profile_demographics(context: Dict[str, Any], postgres_context: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(context, dict):
        context = {}

    profile = {}
    if isinstance(postgres_context, dict):
        profile = postgres_context.get("profile", {})
    if not isinstance(profile, dict):
        profile = {}
    if not profile and isinstance(context.get("patient_profile"), dict):
        profile = context.get("patient_profile", {})

    if not isinstance(profile, dict) or not profile:
        return context

    result = dict(context)
    if result.get("name") in (None, "", [], {}):
        full_name = (
            profile.get("name")
            or profile.get("full_name")
            or profile.get("nombre")
            or profile.get("display_name")
        )
        if not full_name:
            first_name = profile.get("first_name") or profile.get("nombre")
            last_name = profile.get("last_name") or profile.get("apellido")
            parts = [part for part in [first_name, last_name] if isinstance(part, str) and part.strip()]
            if parts:
                full_name = " ".join(parts)
        if isinstance(full_name, str) and full_name.strip():
            result["name"] = full_name.strip()

    if result.get("sex") in (None, "", [], {}):
        sex_value = profile.get("sex") or profile.get("gender") or profile.get("sexo")
        if isinstance(sex_value, str) and sex_value.strip():
            result["sex"] = sex_value.strip()

    if result.get("age") in (None, "", [], {}):
        age_value = profile.get("age") or profile.get("edad")
        if isinstance(age_value, (int, str)) and str(age_value).strip():
            result["age"] = age_value

    return result


def _controller_prefers_expert_on_match() -> bool:
    mode = str(Config.CHAT_CONTROLLER_MODE or "").strip().lower()
    return mode in {
        "expert_owner_on_match",
        "expert_primary",
        "expert_first",
    }


def _extract_prior_state(current_conversation: Dict[str, Any] | None) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], int | None]:
    prior_context: Dict[str, Any] = {}
    prior_expert_state: Dict[str, Any] = {}
    prior_hybrid_state: Dict[str, Any] = {}
    prior_pain: int | None = None

    if not current_conversation:
        return prior_context, prior_expert_state, prior_hybrid_state, prior_pain

    medical_context = current_conversation.get("medical_context", {})
    if not isinstance(medical_context, dict):
        prior_pain = _safe_int_0_10(current_conversation.get("pain_scale"))
        return prior_context, prior_expert_state, prior_hybrid_state, prior_pain

    snapshot = medical_context.get("context_snapshot")
    if isinstance(snapshot, dict):
        prior_context = dict(snapshot)
    else:
        prior_context = {
            key: value for key, value in medical_context.items() if key not in HYBRID_RESERVED_KEYS
        }

    hybrid_state = medical_context.get("hybrid_state")
    if isinstance(hybrid_state, dict):
        prior_hybrid_state = dict(hybrid_state)

    expert_state = prior_hybrid_state.get("expert_state")
    if isinstance(expert_state, dict):
        prior_expert_state = dict(expert_state)
    elif isinstance(medical_context.get("expert_state"), dict):
        prior_expert_state = dict(medical_context.get("expert_state", {}))

    prior_pain = _safe_int_0_10(prior_hybrid_state.get("last_pain_scale"))
    if prior_pain is None:
        prior_pain = _safe_int_0_10(current_conversation.get("pain_scale"))

    return prior_context, prior_expert_state, prior_hybrid_state, prior_pain


def _expert_state_payload(expert_decision) -> Dict[str, Any]:
    state = expert_decision.state
    return {
        "active_case_id": state.active_case_id,
        "active_node_id": state.active_node_id,
        "required_fields_status": state.required_fields_status,
        "confidence": state.confidence,
        "last_rule_ids": state.last_rule_ids,
        "fallback_reason": state.fallback_reason,
        "emergency_triggered": state.emergency_triggered,
        "collected_fields": state.collected_fields,
        "pain_scale": expert_decision.pain_scale,
        "triage_level": state.triage_level,
    }


def _build_expert_response_data(expert_decision, existing_context: Dict[str, Any], expert_state: Dict[str, Any]) -> Dict[str, Any]:
    if expert_decision.action == "fallback_ai":
        return {
            "context": existing_context,
            "triaje_level": expert_decision.triage_level,
            "entities": [],
            "response": "",
            "symptoms": expert_decision.symptoms,
            "symptoms_pattern": {},
            "pain_scale": expert_decision.pain_scale,
            "missing_questions": [],
            "analysis_type": "expert_system",
            "conversation_state": {
                "missing_fields": [k for k, v in expert_decision.state.required_fields_status.items() if not v],
                "collected_fields": [k for k, v in expert_decision.state.required_fields_status.items() if v],
                "next_intent": "collect_missing_data",
                "loop_guard_triggered": False,
                "questions_selected": [],
                "max_questions_per_turn": 2,
                "expert_state": expert_state,
            },
        }

    questions = [expert_decision.response] if expert_decision.action == "ask" and expert_decision.response else []
    return {
        "context": existing_context,
        "triaje_level": expert_decision.triage_level,
        "entities": [],
        "response": expert_decision.response,
        "symptoms": expert_decision.symptoms,
        "symptoms_pattern": {},
        "pain_scale": expert_decision.pain_scale,
        "missing_questions": [],
        "analysis_type": "expert_system",
        "conversation_state": {
            "missing_fields": [k for k, v in expert_decision.state.required_fields_status.items() if not v],
            "collected_fields": [k for k, v in expert_decision.state.required_fields_status.items() if v],
            "next_intent": "collect_missing_data" if expert_decision.action == "ask" else "triage_recommendation",
            "loop_guard_triggered": False,
            "questions_selected": questions,
            "max_questions_per_turn": 2,
            "expert_state": expert_state,
        },
    }


def _extract_questions(payload: Dict[str, Any] | None) -> List[str]:
    if not isinstance(payload, dict):
        return []
    state = payload.get("conversation_state", {})
    if not isinstance(state, dict):
        return []
    questions = state.get("questions_selected", [])
    if not isinstance(questions, list):
        return []
    return [q.strip() for q in questions if isinstance(q, str) and q.strip()]


def _merge_questions(expert_questions: List[str], llm_questions: List[str], max_questions: int = 2) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for q in expert_questions + llm_questions:
        lowered = q.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(q)

    safety = [q for q in ordered if any(hint in q.lower() for hint in SAFETY_QUESTION_HINTS)]
    regular = [q for q in ordered if q not in safety]
    return (safety + regular)[:max_questions]


def _compact_llm_guidance(text: str, max_len: int = 200) -> str:
    if not text:
        return ""
    first_line = text.strip().splitlines()[0].strip()
    if len(first_line) <= max_len:
        return first_line
    return first_line[: max_len - 3].rstrip() + "..."


def _normalize_user_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", lowered) if unicodedata.category(ch) != "Mn"
    )
    no_punct = re.sub(r"[^\w\s]", " ", no_accents)
    return re.sub(r"\s+", " ", no_punct).strip()


def _is_expert_advice_close(
    bot_response: str,
    triage_level: str,
    expert_decision: Any = None,
    expert_cases: Dict[str, Any] | None = None,
) -> bool:
    if expert_decision is None:
        return False

    action = str(getattr(expert_decision, "action", "") or "").strip().lower()
    if action == "advise":
        return True

    case_id = str(getattr(expert_decision, "case_id", "") or "").strip()
    if not case_id:
        return False

    cases = expert_cases or {}
    case_def = cases.get(case_id, {})
    if not isinstance(case_def, dict):
        return False
    advice_map = case_def.get("advice", {})
    if not isinstance(advice_map, dict):
        return False

    bot_norm = _normalize_user_text(bot_response)
    if not bot_norm:
        return False

    triage_norm = _normalize_triage(triage_level)
    candidate_texts: List[str] = []
    primary_advice = advice_map.get(triage_norm)
    if isinstance(primary_advice, str) and primary_advice.strip():
        candidate_texts.append(primary_advice)
    for value in advice_map.values():
        if isinstance(value, str) and value.strip():
            candidate_texts.append(value)

    for candidate in candidate_texts:
        candidate_norm = _normalize_user_text(candidate)
        if not candidate_norm:
            continue
        if bot_norm == candidate_norm or bot_norm.startswith(candidate_norm) or candidate_norm in bot_norm:
            return True
    return False


def _detect_finalization(
    user_message: str,
    bot_response: str,
    conversation_state: Dict[str, Any],
    triage_level: str,
    controller_mode: str,
    expert_decision: Any = None,
    expert_cases: Dict[str, Any] | None = None,
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []

    next_intent = str((conversation_state or {}).get("next_intent", "")).strip().lower()
    if next_intent == "triage_recommendation":
        reasons.append("triage_recommendation")

    if _normalize_triage(triage_level) == "Severo" or str(controller_mode).strip().lower() == "emergency_combined":
        reasons.append("emergency")

    normalized_message = _normalize_user_text(user_message)
    if normalized_message:
        if any(phrase in normalized_message for phrase in EXPLICIT_CLOSE_PHRASES):
            reasons.append("explicit_close_phrase")

    normalized_bot = _normalize_user_text(bot_response)
    if normalized_bot:
        if any(phrase in normalized_bot for phrase in BOT_CLOSE_PHRASES):
            reasons.append("bot_close_phrase")
    if _is_expert_advice_close(
        bot_response,
        triage_level,
        expert_decision=expert_decision,
        expert_cases=expert_cases,
    ):
        reasons.append("expert_advice_close")

    reasons = list(dict.fromkeys(reasons))
    return len(reasons) > 0, reasons


def _extract_turn_number(current_conversation: Dict[str, Any] | None) -> int:
    if not isinstance(current_conversation, dict):
        return 1
    messages = current_conversation.get("messages", [])
    if not isinstance(messages, list):
        return 1
    prior_user_turns = sum(1 for msg in messages if isinstance(msg, dict) and msg.get("role") == "user")
    return prior_user_turns + 1


def _was_pain_question_asked_recently(current_conversation: Dict[str, Any] | None, assistant_window: int = 2) -> bool:
    if not isinstance(current_conversation, dict):
        return False
    messages = current_conversation.get("messages", [])
    if not isinstance(messages, list) or not messages:
        return False
    assistant_messages = [
        msg.get("content", "")
        for msg in reversed(messages)
        if isinstance(msg, dict) and msg.get("role") == "assistant"
    ]
    for content in assistant_messages[:assistant_window]:
        if is_pain_scale_question(content):
            return True
    return False


def _append_missing_questions_to_response(response_text: str, questions_selected: List[str]) -> str:
    if not isinstance(response_text, str):
        response_text = ""
    normalized_response = _normalize_user_text(response_text)
    missing = [
        question for question in questions_selected
        if _normalize_user_text(question) and _normalize_user_text(question) not in normalized_response
    ]
    if not missing:
        return response_text

    if not response_text.strip():
        if len(missing) == 1:
            return f"Para continuar:\n{missing[0]}"
        return f"Para continuar:\n1. {missing[0]}\n2. {missing[1]}"

    if len(missing) == 1:
        return f"{response_text}\n\nPara continuar:\n{missing[0]}"
    return f"{response_text}\n\nPara continuar:\n1. {missing[0]}\n2. {missing[1]}"


LOW_INFORMATION_MESSAGES = {
    "ok",
    "oka",
    "vale",
    "si",
    "sí",
    "de acuerdo",
    "entendido",
    "continua",
    "continúa",
    "sigue",
    "seguir",
}


def _looks_like_progress_prompt(user_message: str) -> bool:
    normalized = _normalize_user_text(user_message)
    if not normalized:
        return False
    if normalized in LOW_INFORMATION_MESSAGES:
        return True
    return "siguiente pregunta" in normalized or "continua" in normalized or "continua con" in normalized


def _find_latest_assistant_question(current_conversation: Dict[str, Any] | None) -> str:
    if not isinstance(current_conversation, dict):
        return ""
    messages = current_conversation.get("messages", [])
    if not isinstance(messages, list):
        return ""

    for msg in reversed(messages):
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        content = str(msg.get("content") or "").strip()
        if "?" in content:
            return content
    return ""


def _build_progress_fallback_response(
    *,
    user_message: str,
    current_conversation: Dict[str, Any] | None,
    context_final: Dict[str, Any],
) -> str:
    latest_question = _find_latest_assistant_question(current_conversation)
    if latest_question and _looks_like_progress_prompt(user_message):
        return f"Para continuar, necesito que respondas a esta pregunta:\n{latest_question}"

    if not context_final.get("symptom_duration"):
        return "Para continuar:\n¿Cuánto tiempo llevas con este síntoma?"

    if context_final.get("pain_level_reported") in (None, "", [], {}) and context_final.get("pain_scale", 0) == 0:
        return "Para continuar:\nEn una escala del 1 al 10, ¿qué tan intenso es el dolor ahora?"

    if not context_final.get("red_flags_checked"):
        return "Para continuar:\n¿Tienes fiebre, dificultad para respirar, dolor en el pecho o te has desmayado?"

    if latest_question:
        return f"Para continuar:\n{latest_question}"

    return "Para continuar:\n¿Qué es lo que más lo empeora o lo mejora?"
