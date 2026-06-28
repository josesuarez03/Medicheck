import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


def _normalize_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", lowered) if unicodedata.category(ch) != "Mn"
    )
    cleaned = re.sub(r"[^a-z0-9\s]", " ", no_accents)
    collapsed = re.sub(r"\s+", " ", cleaned).strip()
    aliases = {
        "me duele la cabeza": "dolor de cabeza",
        "me duele cabeza": "dolor de cabeza",
        "dolor cabeza": "dolor de cabeza",
    }
    for src, target in aliases.items():
        collapsed = collapsed.replace(src, target)
    return collapsed


def _extract_pain_scale(text: str) -> Optional[int]:
    normalized = _normalize_text(text)
    values = [int(raw) for raw in re.findall(r"\b(10|[0-9])\b", normalized)]
    return max(values) if values else None


def _intent_score_for_case(user_message_lower: str, case_def: Dict[str, Any]) -> float:
    keywords = [_normalize_text(str(k)) for k in case_def.get("intent_keywords", []) if str(k).strip()]
    if not keywords:
        return 0.0

    msg_tokens = set(user_message_lower.split())
    if not msg_tokens:
        return 0.0

    total_score = 0.0
    for keyword in keywords:
        if keyword in user_message_lower:
            total_score += 1.0
            continue
        key_tokens = set(keyword.split())
        if not key_tokens:
            continue
        overlap = len(msg_tokens & key_tokens) / len(key_tokens)
        if overlap >= 0.6:
            total_score += overlap
    return round(total_score / len(keywords), 3)


def detect_best_case(
    user_message: str,
    cases: Dict[str, Dict[str, Any]],
    active_case_id: Optional[str] = None,
) -> Tuple[Optional[str], float, float]:
    user_message_lower = _normalize_text(user_message)
    if active_case_id and active_case_id in cases:
        return active_case_id, _intent_score_for_case(user_message_lower, cases[active_case_id]), 0.0

    scored = [(case_id, _intent_score_for_case(user_message_lower, case_def)) for case_id, case_def in cases.items()]
    scored.sort(key=lambda item: item[1], reverse=True)
    if not scored:
        return None, 0.0, 0.0
    best_case_id, best_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0.0
    if best_score <= 0:
        return None, 0.0, second_score
    return best_case_id, best_score, second_score


def infer_pain_level(user_message: str, previous_value: Optional[int] = None) -> int:
    pain_value = _extract_pain_scale(user_message)
    if pain_value is not None:
        return pain_value
    return previous_value if isinstance(previous_value, int) else 0


def _default_keywords_for_field(field_name: str) -> List[str]:
    return {
        "duration": ["dia", "seman", "mes", "hora", "desde", "hace", "ayer", "anoche", "hoy"],
        "associated_symptoms": ["nausea", "vomit", "luz", "ruido", "vision", "mareo"],
        "neurologic_red_flags": ["rigidez de cuello", "debilidad", "hormigueo", "desmayo"],
        "triggers": ["estres", "trabajo", "examen", "discusion", "gatilla", "desencaden"],
        "sleep_impact": ["duermo", "insomnio", "sueno"],
        "functional_impact": ["no puedo", "afecta", "rendimiento", "trabajar", "estudiar", "familia", "social", "funcion"],
        "physical_symptoms": ["palpit", "tembl", "sudor", "opresion", "respirar"],
        "consumption_pattern": ["tomo", "beb", "alcohol", "cerveza", "licor", "copas"],
        "last_intake": ["ultima", "anoche", "hoy", "ayer", "hace"],
        "withdrawal_symptoms": ["tembl", "sudor", "nause", "vomit", "ansiedad", "insomnio", "alucin"],
    }.get(field_name, [])


def _extract_with_rule(
    *,
    field_name: str,
    rule: Dict[str, Any],
    user_message: str,
    user_message_lower: str,
) -> Any:
    extractor_type = str(rule.get("type", "")).strip().lower()
    if extractor_type == "pain_scale":
        pain = infer_pain_level(user_message)
        return pain if pain > 0 else None
    if extractor_type == "categorical_keywords":
        categories = rule.get("categories", {})
        if not isinstance(categories, dict):
            return None
        for category, keywords in categories.items():
            if any(str(k).lower() in user_message_lower for k in (keywords or [])):
                return str(category)
        return None
    if extractor_type == "regex":
        for raw_pattern in rule.get("patterns", []):
            try:
                match = re.search(str(raw_pattern), user_message, re.IGNORECASE)
            except re.error:
                continue
            if not match:
                continue
            group_index = int(rule.get("group", 0))
            value = match.group(group_index)
            if str(rule.get("value_type", "text")).lower() == "int":
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
            return value.strip() if isinstance(value, str) else value

    keywords = [str(k).lower() for k in rule.get("keywords", []) if str(k).strip()]
    if extractor_type in {"keyword_text", "text_if_keyword"}:
        return user_message.strip() if any(keyword in user_message_lower for keyword in keywords) else None
    if extractor_type == "always_text":
        return user_message.strip()

    default_keywords = _default_keywords_for_field(field_name)
    if default_keywords and any(keyword in user_message_lower for keyword in default_keywords):
        return user_message.strip()
    if field_name in {"pain_intensity", "pain_scale"}:
        pain = infer_pain_level(user_message)
        return pain if pain > 0 else None
    return None


def extract_case_fields(
    *,
    case_def: Dict[str, Any],
    user_message: str,
    previous_fields: Optional[Dict[str, Any]] = None,
    expected_field: Optional[str] = None,
) -> Dict[str, Any]:
    text = _normalize_text(user_message)
    fields = dict(previous_fields or {})
    required_fields = [str(field) for field in case_def.get("required_fields", [])]
    extractors = case_def.get("field_extractors", {})
    if not isinstance(extractors, dict):
        extractors = {}

    for field_name in required_fields:
        if fields.get(field_name) not in (None, "", [], {}):
            continue
        rule = extractors.get(field_name, {}) if isinstance(extractors.get(field_name, {}), dict) else {}
        value = _extract_with_rule(
            field_name=field_name,
            rule=rule,
            user_message=user_message,
            user_message_lower=text,
        )
        if value not in (None, "", [], {}):
            fields[field_name] = value

    if expected_field and expected_field in required_fields and fields.get(expected_field) in (None, "", [], {}):
        fields[expected_field] = _extract_with_rule(
            field_name=expected_field,
            rule=extractors.get(expected_field, {}),
            user_message=user_message,
            user_message_lower=text,
        ) or user_message.strip()
    return fields


def classify_triage_level(case_id: str, pain_level: int, user_message: str, triage_policy: Dict[str, Any]) -> str:
    _ = case_id
    text = _normalize_text(user_message)
    severe_threshold = int(triage_policy.get("pain_thresholds", {}).get("severe", 8))
    moderate_threshold = int(triage_policy.get("pain_thresholds", {}).get("moderate", 5))
    if any(marker.lower() in text for marker in triage_policy.get("severe_markers", [])):
        return "Severo"
    if pain_level >= severe_threshold:
        return "Severo"
    if any(marker.lower() in text for marker in triage_policy.get("moderate_markers", [])):
        return "Moderado"
    if pain_level >= moderate_threshold:
        return "Moderado"
    return triage_policy.get("default_triage", "Leve")
