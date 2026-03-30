from typing import Any, Dict, List, Tuple

from config.config import Config
from services.chatbot.application.chat_turn_helpers import _merge_questions, _safe_int_0_10
from services.chatbot.context_manager import PAIN_SCALE_QUESTION, has_explicit_pain_report, is_pain_scale_question
from services.chatbot.pain_utils import extract_pain_scale


def resolve_pain_state(
    user_message: str,
    existing_context: Dict[str, Any],
    prior_pain: int | None,
    expert_response_data: Dict[str, Any],
    llm_response_data: Dict[str, Any] | None,
) -> Tuple[int, int | None, int | None, bool]:
    explicit_pain = extract_pain_scale(user_message)
    prior_reported_pain = _safe_int_0_10(existing_context.get("pain_level_reported"))
    pain_reported = bool(explicit_pain is not None or has_explicit_pain_report(existing_context))
    if explicit_pain is not None:
        pain_scale = explicit_pain
    elif prior_pain is not None:
        pain_scale = prior_pain
    else:
        pain_candidates = [
            _safe_int_0_10(expert_response_data.get("pain_scale")),
            _safe_int_0_10((llm_response_data or {}).get("pain_scale")),
        ]
        pain_scale = next((p for p in pain_candidates if p is not None), 0)

    return pain_scale, explicit_pain, prior_reported_pain, pain_reported


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


def apply_pain_question_policy(
    current_conversation: Dict[str, Any] | None,
    questions_selected: List[str],
    turn_number: int,
    pain_reported: bool,
    decision_reasons: List[str],
    max_questions_per_turn: int = 2,
) -> Tuple[List[str], bool, bool, List[str]]:
    force_pain_by_turn = max(1, int(Config.CHAT_FORCE_PAIN_BY_TURN))
    pain_must_ask = bool(turn_number >= force_pain_by_turn and not pain_reported)

    pain_asked_recently = _was_pain_question_asked_recently(current_conversation)
    pain_already_selected = any(is_pain_scale_question(question) for question in questions_selected)
    pain_asked_now = False
    if pain_must_ask and not pain_asked_recently and not pain_already_selected:
        questions_selected = _merge_questions([PAIN_SCALE_QUESTION], questions_selected, max_questions=max_questions_per_turn)
        pain_asked_now = any(is_pain_scale_question(question) for question in questions_selected)
        if pain_asked_now:
            decision_reasons.append("pain_question_forced_by_turn")
    elif pain_already_selected:
        pain_asked_now = True

    return questions_selected, pain_asked_now, pain_must_ask, decision_reasons
