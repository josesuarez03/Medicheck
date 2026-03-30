from __future__ import annotations

import json
import logging
import re
from functools import lru_cache

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None

try:
    import spacy
    from spacy.matcher import Matcher, PhraseMatcher
except Exception:  # pragma: no cover
    spacy = None
    Matcher = None
    PhraseMatcher = None

from config.config import Config
from services.bedrock_claude import call_claude
from services.duration_utils import extract_duration_text
from services.medical_facts import (
    ClinicalExtractionResult,
    MedicalFact,
    build_facts_summary,
    fact_signature,
    normalize_clinical_text,
)
from services.pain_utils import extract_pain_scale


logger = logging.getLogger(__name__)
_GREETINGS = {"hola", "buenas", "buenos", "saludos", "hey", "gracias", "vale", "ok"}
_BODY_SITES = {"pecho", "cabeza", "espalda", "cuello", "garganta", "abdomen", "estomago"}
_RED_FLAGS = {
    "dolor de pecho",
    "dificultad para respirar",
    "disnea",
    "desmayo",
    "convulsiones",
    "sangrado",
    "debilidad",
    "suicidio",
    "autolesion",
}
_ALLERGY_TERMS = {"alergia", "alergias", "alergico", "alergica"}
_MEDICATION_TERMS = {"paracetamol", "ibuprofeno", "amoxicilina", "omeprazol", "medicacion", "medicamento"}
_HISTORY_TERMS = {"asma", "diabetes", "hipertension", "migraña", "migraña", "ansiedad", "depresion"}
_FUNCTIONAL_TERMS = {"no puedo", "me impide", "me cuesta", "no me deja", "afecta"}
_NEGATION_PATTERN = re.compile(r"\b(no|sin|niego|ningun|ninguna)\b", re.IGNORECASE)


def detect_medical_context(messages):
    context_prompt = f"""
Analiza el siguiente historial y resume solo hechos clínicos persistentes y del episodio actual.
Conversación: {json.dumps(messages, ensure_ascii=False)}
"""
    try:
        return call_claude(context_prompt, max_tokens=180, temperature=0.1)
    except Exception as exc:
        logger.error("Error analyzing medical context: %s", exc)
        return "No se pudo analizar el contexto médico."


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


@lru_cache(maxsize=1)
def _get_matchers():
    nlp = _get_nlp()
    if nlp is None or Matcher is None or PhraseMatcher is None:
        return None, None
    matcher = Matcher(nlp.vocab)
    phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    phrase_matcher.add("RED_FLAG", [nlp.make_doc(term) for term in sorted(_RED_FLAGS)])
    phrase_matcher.add("ALLERGY", [nlp.make_doc(term) for term in sorted(_ALLERGY_TERMS)])
    phrase_matcher.add("MEDICATION", [nlp.make_doc(term) for term in sorted(_MEDICATION_TERMS)])
    phrase_matcher.add("HISTORY", [nlp.make_doc(term) for term in sorted(_HISTORY_TERMS)])
    return matcher, phrase_matcher


def split_for_clinical_analysis(text: str) -> tuple[list[dict], list[str]]:
    segments: list[dict] = []
    discarded: list[str] = []
    cursor = 0
    for raw_segment in re.split(r"(?<=[.!?;,])\s+|\n+", text or ""):
        segment = raw_segment.strip()
        if not segment:
            cursor += len(raw_segment) + 1
            continue
        lowered = normalize_clinical_text(segment)
        if lowered in _GREETINGS or len(re.sub(r"\W", "", lowered)) < 3:
            discarded.append(segment)
            cursor += len(raw_segment) + 1
            continue
        start = (text or "").find(segment, cursor)
        start = cursor if start < 0 else start
        end = start + len(segment)
        segments.append({"text": segment, "start": start, "end": end})
        cursor = end
    return segments, discarded


def _temporality(text: str) -> str:
    normalized = normalize_clinical_text(text)
    if re.search(r"\b(cronico|cronica|siempre|desde hace meses|desde hace anos)\b", normalized):
        return "chronic"
    if re.search(r"\b(ayer|anoche|hace|desde|hoy|esta manana|esta tarde)\b", normalized):
        return "recent"
    if re.search(r"\b(antes|hace anos|previo|previa)\b", normalized):
        return "past"
    if re.search(r"\b(actual|ahora|mismo)\b", normalized):
        return "current"
    return "unknown"


def _negated(text: str) -> bool:
    return bool(_NEGATION_PATTERN.search(normalize_clinical_text(text)))


def _fact(
    *,
    text: str,
    category: str,
    role: str,
    source: str,
    confidence: float,
    start: int | None = None,
    end: int | None = None,
    value=None,
    unit: str | None = None,
    context_text: str | None = None,
) -> MedicalFact:
    effective_text = context_text or text
    return MedicalFact(
        text=text,
        normalized_text=normalize_clinical_text(text),
        category=category,
        clinical_role=role,
        value=value,
        unit=unit,
        temporality=_temporality(effective_text),
        negated=_negated(effective_text),
        confidence=confidence,
        source=source,
        span_start=start,
        span_end=end,
    )


def extract_with_spacy(text: str) -> list[MedicalFact]:
    nlp = _get_nlp()
    if nlp is None:
        return _extract_with_rules_only(text)

    doc = nlp(text)
    _, phrase_matcher = _get_matchers()
    facts: list[MedicalFact] = []
    pain_scale = extract_pain_scale(text)
    if pain_scale is not None:
        facts.append(_fact(text=str(pain_scale), category="SEVERITY", role="pain_scale", source="rule", confidence=0.82, value=pain_scale))
    duration = extract_duration_text(text)
    if duration:
        facts.append(_fact(text=duration, category="DURATION", role="duration", source="rule", confidence=0.8))

    if phrase_matcher is not None:
        for match_id, start, end in phrase_matcher(doc):
            label = doc.vocab.strings[match_id]
            span = doc[start:end]
            if label == "RED_FLAG":
                facts.append(_fact(text=span.text, category="RED_FLAG", role="red_flag", source="spacy", confidence=0.86, start=span.start_char, end=span.end_char, context_text=text))
            elif label == "ALLERGY":
                facts.append(_fact(text=span.text, category="ALLERGY", role="allergy", source="spacy", confidence=0.76, start=span.start_char, end=span.end_char, context_text=text))
            elif label == "MEDICATION":
                facts.append(_fact(text=span.text, category="MEDICATION", role="medication", source="spacy", confidence=0.76, start=span.start_char, end=span.end_char, context_text=text))
            elif label == "HISTORY":
                facts.append(_fact(text=span.text, category="MEDICAL_HISTORY", role="history", source="spacy", confidence=0.72, start=span.start_char, end=span.end_char, context_text=text))

    normalized = normalize_clinical_text(text)
    for body_site in _BODY_SITES:
        if body_site in normalized:
            facts.append(_fact(text=body_site, category="BODY_SITE", role="context", source="rule", confidence=0.65, context_text=text))

    if "dolor" in normalized:
        role = "chief_complaint" if any(term in normalized for term in ("dolor", "molestia", "opresion")) else "secondary_symptom"
        facts.append(_fact(text=text, category="SYMPTOM", role=role, source="spacy", confidence=0.68, context_text=text))
    for symptom in ("fiebre", "mareo", "tos", "nausea", "vomito", "disnea", "palpitaciones", "ansiedad"):
        if symptom in normalized:
            facts.append(_fact(text=symptom, category="SYMPTOM", role="secondary_symptom", source="rule", confidence=0.62, context_text=text))

    for term in _FUNCTIONAL_TERMS:
        if term in normalized:
            facts.append(_fact(text=term, category="FUNCTIONAL_IMPACT", role="context", source="rule", confidence=0.6, context_text=text))

    for allergy in _ALLERGY_TERMS:
        if allergy in normalized:
            facts.append(_fact(text=allergy, category="ALLERGY", role="allergy", source="rule", confidence=0.7, context_text=text))

    for medication in _MEDICATION_TERMS:
        if medication in normalized:
            facts.append(_fact(text=medication, category="MEDICATION", role="medication", source="rule", confidence=0.7, context_text=text))

    for history_term in _HISTORY_TERMS:
        if history_term in normalized:
            facts.append(_fact(text=history_term, category="MEDICAL_HISTORY", role="history", source="rule", confidence=0.68, context_text=text))

    for token in doc:
        lowered = token.text.lower()
        if lowered in {"fuerte", "muy", "intenso", "insoportable", "leve", "moderado"}:
            facts.append(_fact(text=token.text, category="SEVERITY", role="context", source="spacy", confidence=0.58, context_text=text))
    return facts


def _map_comprehend_category(entity: dict) -> tuple[str, str]:
    entity_type = str(entity.get("Type", "")).upper()
    category = str(entity.get("Category", "")).upper()
    if entity_type in {"DX_NAME", "MEDICAL_CONDITION"}:
        return "SYMPTOM", "secondary_symptom"
    if entity_type == "MEDICATION":
        return "MEDICATION", "medication"
    if entity_type == "TEST_TREATMENT_PROCEDURE_NAME":
        return "MEDICAL_HISTORY", "history"
    if entity_type == "AGE" or category == "PROTECTED_HEALTH_INFORMATION":
        return "DEMOGRAPHIC", "demographic"
    return "UNKNOWN", "context"


def extract_with_comprehend(text: str) -> list[MedicalFact]:
    if boto3 is None or not Config.AWS_REGION:
        return []
    try:
        client = boto3.client("comprehendmedical", region_name=Config.AWS_REGION)
        result = client.detect_entities(Text=text)
    except Exception as exc:
        logger.warning("Comprehend Medical unavailable, using local extraction only: %s", exc)
        return []

    facts: list[MedicalFact] = []
    for entity in result.get("Entities", []):
        raw_text = entity.get("Text", "") or ""
        category, role = _map_comprehend_category(entity)
        fact = _fact(
            text=raw_text,
            category=category,
            role=role,
            source="comprehend",
            confidence=float(entity.get("Score", 0.55)),
            start=entity.get("BeginOffset"),
            end=entity.get("EndOffset"),
        )
        traits = entity.get("Traits", []) or []
        if any(str(item.get("Name", "")).upper() == "NEGATION" for item in traits):
            fact.negated = True
        facts.append(fact)

        for attribute in entity.get("Attributes", []) or []:
            attr_text = attribute.get("Text", "") or ""
            attr_type = str(attribute.get("Type", "")).upper()
            if attr_type == "DOSAGE":
                facts.append(_fact(text=attr_text, category="SEVERITY", role="context", source="comprehend", confidence=float(attribute.get("Score", 0.5))))
    return facts


def _extract_with_rules_only(text: str) -> list[MedicalFact]:
    facts: list[MedicalFact] = []
    normalized = normalize_clinical_text(text)
    pain_scale = extract_pain_scale(text)
    if pain_scale is not None:
        facts.append(_fact(text=str(pain_scale), category="SEVERITY", role="pain_scale", source="rule", confidence=0.8, value=pain_scale, context_text=text))
    duration = extract_duration_text(text)
    if duration:
        facts.append(_fact(text=duration, category="DURATION", role="duration", source="rule", confidence=0.8, context_text=text))
    if "dolor" in normalized:
        facts.append(_fact(text=text, category="SYMPTOM", role="chief_complaint", source="rule", confidence=0.7, context_text=text))
    for flag in _RED_FLAGS:
        if flag in normalized:
            facts.append(_fact(text=flag, category="RED_FLAG", role="red_flag", source="rule", confidence=0.8, context_text=text))
    for med in _MEDICATION_TERMS:
        if med in normalized:
            facts.append(_fact(text=med, category="MEDICATION", role="medication", source="rule", confidence=0.65, context_text=text))
    for allergy in _ALLERGY_TERMS:
        if allergy in normalized:
            facts.append(_fact(text=allergy, category="ALLERGY", role="allergy", source="rule", confidence=0.65, context_text=text))
    for history_term in _HISTORY_TERMS:
        if history_term in normalized:
            facts.append(_fact(text=history_term, category="MEDICAL_HISTORY", role="history", source="rule", confidence=0.65, context_text=text))
    return facts


def merge_medical_facts(spacy_facts: list[MedicalFact], comprehend_facts: list[MedicalFact]) -> list[MedicalFact]:
    merged: dict[str, MedicalFact] = {}
    for fact in spacy_facts + comprehend_facts:
        signature = fact_signature(fact)
        if signature not in merged:
            merged[signature] = fact
            continue
        current = merged[signature]
        current.confidence = round(max(current.confidence, fact.confidence), 3)
        if current.source != fact.source:
            current.source = "hybrid"
            current.confidence = round(min(0.99, current.confidence + 0.08), 3)
        if current.span_start is None:
            current.span_start = fact.span_start
        if current.span_end is None:
            current.span_end = fact.span_end
    return list(merged.values())


def detect_entities(text, context=None):
    segments, discarded = split_for_clinical_analysis(text)
    all_spacy_facts: list[MedicalFact] = []
    all_comprehend_facts: list[MedicalFact] = []
    for segment in segments:
        segment_text = segment["text"]
        all_spacy_facts.extend(extract_with_spacy(segment_text))
        if len(re.sub(r"\W", "", normalize_clinical_text(segment_text))) >= 3:
            all_comprehend_facts.extend(extract_with_comprehend(segment_text))

    facts = merge_medical_facts(all_spacy_facts, all_comprehend_facts)
    summary = build_facts_summary(facts)
    context_analysis = detect_medical_context([{"content": text}]) if context else None
    result = ClinicalExtractionResult(
        facts=facts,
        facts_summary=summary,
        discarded_segments=discarded,
        context_analysis=context_analysis,
    )
    return result.model_dump()


def analyze_text(text, context=None):
    return detect_entities(text, context)
