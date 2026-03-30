from typing import Any, Dict, List, Tuple

from config.config import Config


def _controller_prefers_expert_on_match() -> bool:
    mode = str(Config.CHAT_CONTROLLER_MODE or "").strip().lower()
    return mode in {
        "expert_owner_on_match",
        "expert_primary",
        "expert_first",
    }


def normalize_prior_controller_mode(prior_hybrid_state: Dict[str, Any]) -> str:
    prior_controller_mode = str(prior_hybrid_state.get("controller_mode") or "llm_primary")
    if prior_controller_mode not in {"llm_primary", "expert_primary", "expert_fallback", "emergency_combined"}:
        return "llm_primary"
    return prior_controller_mode


def decide_controller_mode(
    expert_decision: Any,
    llm_response_data: Dict[str, Any] | None,
    triage_final: str,
) -> Tuple[str, str, List[str], str, str]:
    expert_action = str(expert_decision.action or "").strip().lower()
    expert_emergency = bool(expert_decision.emergency_triggered or expert_action == "escalate")
    expert_case_match = bool(expert_decision.case_id and expert_action in {"ask", "advise"})
    expert_confident_match = expert_case_match and not bool(expert_decision.fallback_reason)
    prefer_expert_on_match = _controller_prefers_expert_on_match()

    decision_reasons: List[str] = []
    if expert_emergency and str(Config.CHAT_EMERGENCY_MODE).strip().lower() == "combined":
        controller_mode = "emergency_combined"
        owner = "combined_emergency"
        decision_reasons.append("emergency_detected")
        triage_final = "Severo"
    elif prefer_expert_on_match and expert_confident_match:
        controller_mode = "expert_primary"
        owner = "expert_primary"
        decision_reasons.append("expert_confident_case_match")
    elif llm_response_data:
        controller_mode = "llm_primary"
        owner = "llm_primary"
        decision_reasons.append("llm_default")
    else:
        controller_mode = "expert_fallback"
        owner = "expert_fallback"
        decision_reasons.append("llm_unavailable_expert_fallback")

    return controller_mode, owner, decision_reasons, expert_action, triage_final
