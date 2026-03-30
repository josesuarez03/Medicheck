from __future__ import annotations

import re
import unicodedata
import uuid
from typing import Literal

from pydantic import BaseModel, Field


FactCategory = Literal[
    "SYMPTOM",
    "MEDICATION",
    "ALLERGY",
    "MEDICAL_HISTORY",
    "BODY_SITE",
    "SEVERITY",
    "DURATION",
    "VITAL_SIGN",
    "RISK_FACTOR",
    "TRIGGER",
    "FUNCTIONAL_IMPACT",
    "RED_FLAG",
    "DEMOGRAPHIC",
    "UNKNOWN",
]

ClinicalRole = Literal[
    "chief_complaint",
    "secondary_symptom",
    "medication",
    "allergy",
    "history",
    "duration",
    "pain_scale",
    "red_flag",
    "demographic",
    "context",
]

Temporality = Literal["current", "recent", "past", "chronic", "unknown"]
FactSource = Literal["comprehend", "spacy", "rule", "hybrid"]


class MedicalFact(BaseModel):
    fact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    normalized_text: str
    category: FactCategory
    clinical_role: ClinicalRole
    value: str | int | float | None = None
    unit: str | None = None
    temporality: Temporality = "unknown"
    negated: bool = False
    confidence: float = 0.5
    source: FactSource = "rule"
    span_start: int | None = None
    span_end: int | None = None


class FactsSummary(BaseModel):
    chief_complaints: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    history: list[str] = Field(default_factory=list)
    pain_scale: int | None = None
    duration: str | None = None
    red_flags: list[str] = Field(default_factory=list)
    body_sites: list[str] = Field(default_factory=list)
    severity_terms: list[str] = Field(default_factory=list)
    functional_impact: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)


class ClinicalExtractionResult(BaseModel):
    facts: list[MedicalFact] = Field(default_factory=list)
    facts_summary: FactsSummary = Field(default_factory=FactsSummary)
    discarded_segments: list[str] = Field(default_factory=list)
    context_analysis: str | None = None


def normalize_clinical_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", lowered) if unicodedata.category(ch) != "Mn"
    )
    cleaned = re.sub(r"[^a-z0-9\s/%.-]", " ", no_accents)
    return re.sub(r"\s+", " ", cleaned).strip()


def dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = normalize_clinical_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(value.strip())
    return ordered


def fact_signature(fact: MedicalFact) -> str:
    return "|".join(
        [
            fact.category,
            fact.clinical_role,
            fact.normalized_text,
            fact.temporality,
            str(fact.negated),
        ]
    )


def build_facts_summary(facts: list[MedicalFact]) -> FactsSummary:
    summary = FactsSummary()
    for fact in facts:
        if fact.negated:
            continue
        if fact.clinical_role == "chief_complaint":
            summary.chief_complaints.append(fact.normalized_text)
        elif fact.category == "SYMPTOM":
            summary.symptoms.append(fact.normalized_text)
        elif fact.category == "MEDICATION":
            summary.medications.append(fact.normalized_text)
        elif fact.category == "ALLERGY":
            summary.allergies.append(fact.normalized_text)
        elif fact.category == "MEDICAL_HISTORY":
            summary.history.append(fact.normalized_text)
        elif fact.category == "BODY_SITE":
            summary.body_sites.append(fact.normalized_text)
        elif fact.category == "SEVERITY":
            summary.severity_terms.append(fact.normalized_text)
        elif fact.category == "FUNCTIONAL_IMPACT":
            summary.functional_impact.append(fact.normalized_text)
        elif fact.category == "RISK_FACTOR":
            summary.risk_factors.append(fact.normalized_text)
        elif fact.category == "RED_FLAG":
            summary.red_flags.append(fact.normalized_text)

        if fact.clinical_role == "pain_scale" and isinstance(fact.value, (int, float)):
            fact_value = int(fact.value)
            summary.pain_scale = max(summary.pain_scale or 0, fact_value)
        if fact.clinical_role == "duration" and not summary.duration:
            summary.duration = fact.text.strip()

    summary.chief_complaints = dedupe_keep_order(summary.chief_complaints)
    summary.symptoms = dedupe_keep_order(summary.symptoms)
    summary.medications = dedupe_keep_order(summary.medications)
    summary.allergies = dedupe_keep_order(summary.allergies)
    summary.history = dedupe_keep_order(summary.history)
    summary.red_flags = dedupe_keep_order(summary.red_flags)
    summary.body_sites = dedupe_keep_order(summary.body_sites)
    summary.severity_terms = dedupe_keep_order(summary.severity_terms)
    summary.functional_impact = dedupe_keep_order(summary.functional_impact)
    summary.risk_factors = dedupe_keep_order(summary.risk_factors)
    return summary
