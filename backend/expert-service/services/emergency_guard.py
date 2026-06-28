from typing import Any, Dict, List, Optional, Tuple


def detect_emergency(
    user_message_lower: str,
    emergency_rules: Dict[str, Any],
    case_id: Optional[str] = None,
) -> Tuple[bool, List[str], bool]:
    matched_rules: List[str] = []
    is_psychological = False
    psychological_case_ids = {
        str(case).strip()
        for case in emergency_rules.get("psychological_case_ids", [])
        if str(case).strip()
    }

    for item in emergency_rules.get("global_red_flags", []):
        keyword = str(item.get("keyword", "")).lower()
        if keyword and keyword in user_message_lower:
            matched_rules.append(str(item.get("rule_id", "global_emergency_rule")))

    if case_id:
        if case_id in psychological_case_ids:
            is_psychological = True
        for item in emergency_rules.get("case_red_flags", {}).get(case_id, []):
            keyword = str(item.get("keyword", "")).lower()
            if keyword and keyword in user_message_lower:
                matched_rules.append(str(item.get("rule_id", f"{case_id}_emergency_rule")))
                if bool(item.get("psychological", False)):
                    is_psychological = True

    for item in emergency_rules.get("psychological_crisis_flags", []):
        keyword = str(item.get("keyword", "")).lower()
        if keyword and keyword in user_message_lower:
            matched_rules.append(str(item.get("rule_id", "psych_crisis_rule")))
            is_psychological = True

    return len(matched_rules) > 0, list(dict.fromkeys(matched_rules)), is_psychological


def build_emergency_message(emergency_rules: Dict[str, Any], psychological: bool = False) -> str:
    messages = emergency_rules.get("messages", {})
    base = messages.get(
        "base",
        "Tus síntomas podrían indicar una situación urgente. Busca atención médica inmediata o llama al 112/911 ahora.",
    )
    if psychological:
        psych = messages.get(
            "psychological",
            "Si hay riesgo de autolesión o daño inminente, llama al 112/911 de inmediato.",
        )
        return f"{base}\n{psych}"
    return base
