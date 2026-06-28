import re
from typing import List, Optional


PAIN_KEYWORD_SCORES = {
    "insoportable": 9,
    "muy fuerte": 8,
    "intenso": 8,
    "fuerte": 6,
    "moderado": 5,
    "leve": 2,
    "suave": 2,
    "ligero": 2,
    "molesto": 3,
}


def _dedupe_keep_order(values: List[int]) -> List[int]:
    seen = set()
    ordered: List[int] = []
    for value in values:
        if not isinstance(value, int) or not (0 <= value <= 10):
            continue
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def extract_pain_scales(text: str) -> List[int]:
    """Extract all explicit/implicit pain levels from natural language text."""
    normalized = (text or "").strip().lower()
    if not normalized:
        return []

    values: List[int] = []

    contextual_matches = re.finditer(
        r"(?:dolor|intensidad|escala|nivel|ahora|ahorita|actualmente|reposo|ejercicio|esfuerzo)[^\d]{0,18}(10|[0-9])",
        normalized,
    )
    for match in contextual_matches:
        values.append(int(match.group(1)))

    direct = re.fullmatch(r"(?:un|una)?\s*(10|[0-9])", normalized)
    if direct:
        values.append(int(direct.group(1)))

    # Accept short free-form replies like "es un 4" or "como 6" when the message is brief.
    short_reply = re.fullmatch(
        r"(?:es|sera|seria|como|aprox(?:imadamente)?|mas o menos|ahora es|ahorita es)?\s*(?:un|una)?\s*(10|[0-9])",
        normalized,
    )
    if short_reply:
        values.append(int(short_reply.group(1)))

    if not values:
        # Secondary pass for short messages that mention multiple scale values in one sentence.
        numeric_tokens = [int(raw) for raw in re.findall(r"\b(10|[0-9])\b", normalized)]
        if 1 <= len(numeric_tokens) <= 3 and any(
            marker in normalized for marker in ("dolor", "escala", "intensidad", "ahora", "ahorita", "ejercicio", "esfuerzo")
        ):
            values.extend(numeric_tokens)

    values = _dedupe_keep_order(values)
    if values:
        return values

    for keyword, score in PAIN_KEYWORD_SCORES.items():
        if keyword in normalized:
            return [score]

    return []


def extract_pain_scale(text: str) -> Optional[int]:
    """Extract pain scale using the most severe value when multiple are reported."""
    values = extract_pain_scales(text)
    if not values:
        return None
    return max(values)
