import re
import unicodedata
from typing import Any, Dict, List, Tuple

from services.chatbot.application.chat_turn_helpers import _normalize_triage

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


def detect_finalization(
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
