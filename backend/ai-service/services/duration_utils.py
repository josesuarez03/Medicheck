import re
import unicodedata
from typing import Optional


def _normalize_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", lowered) if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"\s+", " ", no_accents).strip()


def extract_duration_text(text: str) -> Optional[str]:
    """
    Detects temporal/duration expressions in Spanish free text.
    Returns original trimmed input if a duration clue is found; otherwise None.
    """
    if not text or not text.strip():
        return None

    original = text.strip()
    normalized = _normalize_text(original)

    # Explicit temporal anchors.
    temporal_anchors = [
        r"\bdesde\b",
        r"\bhace\b",
        r"\bdurante\b",
        r"\bpor\b",
        r"\bayer\b",
        r"\banoche\b",
        r"\bhoy\b",
        r"\besta (?:manana|tarde|noche)\b",
        r"\bmedia hora\b",
        r"\bun rato\b",
    ]
    if any(re.search(pattern, normalized) for pattern in temporal_anchors):
        return original

    # Numeric + duration units with optional spaces (e.g. "2 horas", "48h", "3d", "2 sem").
    unit_pattern = (
        r"\b\d+\s*("
        r"seg(?:undo)?s?|"
        r"min(?:uto)?s?|"
        r"h(?:ora)?s?|hr?s?|"
        r"d(?:ia)?s?|"
        r"sem(?:ana)?s?|"
        r"mes(?:es)?|"
        r"a(?:n|ñ)o?s?"
        r")\b"
    )
    if re.search(unit_pattern, normalized):
        return original

    # Compact formats frequently used in chat (e.g. 24h, 7d, 2sem, 3mes).
    compact_pattern = r"\b\d+(?:h|hr|hrs|d|sem|mes|ano|anos|año|años)\b"
    if re.search(compact_pattern, normalized):
        return original

    # Qualitative quantities with units (e.g. "varios dias", "unas semanas").
    qualitative_pattern = (
        r"\b(?:varios|varias|unos|unas|algunos|algunas)\s+"
        r"(?:dias|horas|minutos|semanas|meses|anos|años)\b"
    )
    if re.search(qualitative_pattern, normalized):
        return original

    return None
