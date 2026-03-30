from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field

try:
    import spacy
except Exception:  # pragma: no cover
    spacy = None


HARMFUL_PATTERNS = [
    r"<script>",
    r"javascript:",
    r"onerror=",
    r"\b(select|drop|union|insert|delete)\b",
]
GREETING_WORDS = {"hola", "buenas", "buenos", "saludos", "hey", "hi", "hello"}
LOW_SIGNAL_WORDS = {"ok", "vale", "gracias", "entendido", "perfecto", "bien"}
DIAGNOSIS_LEMMAS = {"diagnostico", "enfermedad", "diagnosticar"}
MEDICATION_LEMMAS = {"medicacion", "tratamiento", "dosis", "medicamento", "recetar"}
DIAGNOSIS_PATTERNS = (
    r"\bdiagnostic",
    r"\bque (?:tengo|puede ser)\b",
    r"\bque enfermedad\b",
)
MEDICATION_PATTERNS = (
    r"\brecet",
    r"\bdosis\b",
    r"\bmedic",
    r"\btratamiento\b",
)
CLINICAL_HINTS = {
    "dolor",
    "fiebre",
    "mareo",
    "tos",
    "vomito",
    "vomitar",
    "nausea",
    "disnea",
    "pecho",
    "cabeza",
    "alergia",
    "medicamento",
    "palpitacion",
    "ansiedad",
    "sangrado",
    "presion",
    "falta",
}


class MessageAnalysis(BaseModel):
    is_valid: bool
    analysis_type: Literal[
        "greeting",
        "clinical",
        "non_clinical",
        "diagnosis_restriction",
        "medication_restriction",
        "input_error",
    ]
    clinical_signal_score: float = 0.0
    tokens: list[str] = Field(default_factory=list)
    lemmas: list[str] = Field(default_factory=list)
    discarded_reasons: list[str] = Field(default_factory=list)
    error_message: str = ""


def normalize_text(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", (text or "").strip()) if unicodedata.category(char) != "Mn"
    ).lower()


@lru_cache(maxsize=1)
def _get_nlp():
    if spacy is None:
        return None
    for model_name in ("es_core_news_md", "es_core_news_sm"):
        try:
            return spacy.load(model_name)
        except Exception:
            continue
    try:
        return spacy.blank("es")
    except Exception:
        return None


def _fallback_tokens(text: str) -> list[str]:
    return re.findall(r"\b[\wáéíóúüñ]+\b", text.lower(), re.UNICODE)


def _extract_tokens_and_lemmas(text: str) -> tuple[list[str], list[str]]:
    nlp = _get_nlp()
    if nlp is None:
        tokens = _fallback_tokens(text)
        return tokens, tokens
    doc = nlp(text)
    tokens = [token.text.lower() for token in doc if not token.is_space]
    lemmas = []
    for token in doc:
        if token.is_space:
            continue
        lemma = token.lemma_.lower().strip() if token.lemma_ else token.text.lower()
        lemmas.append(lemma)
    return tokens, lemmas


def _has_harmful_pattern(text: str) -> bool:
    normalized = normalize_text(text)
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in HARMFUL_PATTERNS)


def _is_greeting(tokens: list[str]) -> bool:
    return 0 < len(tokens) <= 3 and all(token in GREETING_WORDS for token in tokens)


def _is_low_signal(tokens: list[str]) -> bool:
    return 0 < len(tokens) <= 3 and all(token in LOW_SIGNAL_WORDS for token in tokens)


def _clinical_signal_score(tokens: list[str], lemmas: list[str], normalized: str) -> float:
    score = 0.0
    token_set = set(tokens) | set(lemmas)
    hits = len(CLINICAL_HINTS & token_set)
    if hits:
        score += min(0.6, 0.15 * hits)
    if re.search(r"\b(10|[0-9])\s*/\s*10\b", normalized):
        score += 0.2
    if re.search(r"\b(hace|desde|ayer|anoche|hoy|dias|horas|semanas|meses)\b", normalized):
        score += 0.15
    if re.search(r"\b(no|sin|niego)\b", normalized):
        score += 0.05
    if re.search(r"\b(dificultad para respirar|dolor de pecho|sangrado|desmayo|convulsion)\b", normalized):
        score += 0.3
    return round(min(1.0, score), 2)


def analyze_message(text: str) -> MessageAnalysis:
    if not text or text.isspace():
        return MessageAnalysis(
            is_valid=False,
            analysis_type="input_error",
            discarded_reasons=["empty_message"],
            error_message="El mensaje no puede estar vacío.",
        )
    if len(text) > 500:
        return MessageAnalysis(
            is_valid=False,
            analysis_type="input_error",
            discarded_reasons=["too_long"],
            error_message="El mensaje es demasiado largo. Límite máximo: 500 caracteres.",
        )
    if _has_harmful_pattern(text):
        return MessageAnalysis(
            is_valid=False,
            analysis_type="input_error",
            discarded_reasons=["harmful_pattern"],
            error_message="Entrada no válida: se detectaron patrones potencialmente dañinos.",
        )
    if re.search(r"(.)\1{4,}", text):
        return MessageAnalysis(
            is_valid=False,
            analysis_type="input_error",
            discarded_reasons=["excessive_repetition"],
            error_message="No se permiten repeticiones excesivas de caracteres.",
        )

    normalized = normalize_text(text)
    tokens, lemmas = _extract_tokens_and_lemmas(text)
    score = _clinical_signal_score(tokens, lemmas, normalized)

    if _is_greeting(tokens):
        return MessageAnalysis(
            is_valid=True,
            analysis_type="greeting",
            clinical_signal_score=0.05,
            tokens=tokens,
            lemmas=lemmas,
            discarded_reasons=["greeting_only"],
        )

    if DIAGNOSIS_LEMMAS & set(lemmas) or any(re.search(pattern, normalized) for pattern in DIAGNOSIS_PATTERNS):
        return MessageAnalysis(
            is_valid=True,
            analysis_type="diagnosis_restriction",
            clinical_signal_score=max(score, 0.2),
            tokens=tokens,
            lemmas=lemmas,
        )

    if MEDICATION_LEMMAS & set(lemmas) or any(re.search(pattern, normalized) for pattern in MEDICATION_PATTERNS):
        return MessageAnalysis(
            is_valid=True,
            analysis_type="medication_restriction",
            clinical_signal_score=max(score, 0.2),
            tokens=tokens,
            lemmas=lemmas,
        )

    if _is_low_signal(tokens):
        return MessageAnalysis(
            is_valid=True,
            analysis_type="non_clinical",
            clinical_signal_score=0.05,
            tokens=tokens,
            lemmas=lemmas,
            discarded_reasons=["low_signal_message"],
        )

    analysis_type: Literal["clinical", "non_clinical"] = "clinical" if score >= 0.15 else "non_clinical"
    return MessageAnalysis(
        is_valid=True,
        analysis_type=analysis_type,
        clinical_signal_score=score,
        tokens=tokens,
        lemmas=lemmas,
    )


def generate_response(text: str) -> str:
    analysis = analyze_message(text)
    if analysis.analysis_type == "input_error":
        return analysis.error_message
    if analysis.analysis_type == "greeting":
        return "Hola, soy Hipo. Cuéntame el síntoma o molestia principal para orientarte mejor."
    if analysis.analysis_type == "diagnosis_restriction":
        return "No puedo dar diagnósticos médicos. Puedo ayudarte a ordenar síntomas y nivel de urgencia."
    if analysis.analysis_type == "medication_restriction":
        return "No puedo recetar ni indicar dosis. Sí puedo orientarte sobre síntomas y cuándo consultar."
    if analysis.analysis_type == "non_clinical":
        return "Cuando quieras, descríbeme el síntoma principal, cuánto tiempo llevas así y la intensidad."
    return "Gracias. Voy a centrarme en los síntomas, su duración y la urgencia para orientarte mejor."
