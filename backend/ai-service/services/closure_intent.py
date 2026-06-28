from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from services.comprehend_medical import detect_entities
from services.input_validate import analyze_message
from services.medical_facts import FactsSummary, normalize_clinical_text


ClosureIntentName = Literal["closure", "clinical", "ambiguous_question", "ambiguous_clinical", "uncertain"]

_CLOSURE_PATTERNS = (
    r"^(ok|vale|perfecto|entendido|de acuerdo|gracias|ok gracias|vale gracias|gracias hipo)[.! ]*$",
    r"^(ok[, ]+gracias|vale[, ]+perfecto|perfecto[, ]+gracias)[.! ]*$",
    r"^(?:nada mas|nada más|mas nada|no tengo mas|no tengo más|eso es todo|seria todo|sería todo|eso seria todo|eso sería todo)(?:[,.! ]+(?:gracias|ok|vale|perfecto))?[.! ]*$",
    r"^(?:ya no|ya no mas|ya no más)(?: tengo| hay)?(?: nada)?(?:[,.! ]+(?:gracias|ok|vale))?[.! ]*$",
)
_QUESTION_HINTS = (
    r"\?$",
    r"\b(es grave|que hago|que significa|por que|puede ser|debo ir)\b",
)


class ClosureIntentResult(BaseModel):
    intent: ClosureIntentName
    confidence: float
    should_trigger_etl: bool = False
    should_continue_session: bool = False
    should_ask_explicit_confirmation: bool = False
    facts_summary: FactsSummary = Field(default_factory=FactsSummary)
    analysis_type: str = "non_clinical"
    rationale: list[str] = Field(default_factory=list)


def _has_clinical_facts(summary: FactsSummary) -> bool:
    return any(
        [
            bool(summary.chief_complaints),
            bool(summary.symptoms),
            bool(summary.red_flags),
            bool(summary.body_sites),
            bool(summary.history),
            bool(summary.medications),
            bool(summary.allergies),
            bool(summary.duration),
            summary.pain_scale is not None,
            bool(summary.functional_impact),
            bool(summary.severity_terms),
        ]
    )


def classify_closure_message(text: str, existing_context: dict | None = None) -> ClosureIntentResult:
    normalized = normalize_clinical_text(text)
    analysis = analyze_message(text)
    extraction = detect_entities(text, context=existing_context)
    facts_summary = FactsSummary(**(extraction.get("facts_summary", {}) or {}))
    has_clinical_facts = _has_clinical_facts(facts_summary)
    has_closure_phrase = any(re.search(pattern, normalized) for pattern in _CLOSURE_PATTERNS)
    has_question = any(re.search(pattern, normalized) for pattern in _QUESTION_HINTS)
    rationale: list[str] = []

    if has_clinical_facts:
        rationale.append("clinical_facts_detected")
        if has_closure_phrase or has_question:
            return ClosureIntentResult(
                intent="ambiguous_clinical",
                confidence=0.9,
                should_continue_session=True,
                facts_summary=facts_summary,
                analysis_type=analysis.analysis_type,
                rationale=rationale + ["mixed_closure_and_clinical_signal"],
            )
        return ClosureIntentResult(
            intent="clinical",
            confidence=0.96,
            should_continue_session=True,
            facts_summary=facts_summary,
            analysis_type=analysis.analysis_type,
            rationale=rationale,
        )

    if has_question:
        return ClosureIntentResult(
            intent="ambiguous_question",
            confidence=0.9,
            facts_summary=facts_summary,
            analysis_type=analysis.analysis_type,
            rationale=["question_detected"],
        )

    if has_closure_phrase or "low_signal_message" in analysis.discarded_reasons:
        return ClosureIntentResult(
            intent="closure",
            confidence=0.94 if has_closure_phrase else 0.88,
            should_trigger_etl=True,
            facts_summary=facts_summary,
            analysis_type=analysis.analysis_type,
            rationale=["closure_phrase" if has_closure_phrase else "explicit_low_signal_ack"],
        )

    return ClosureIntentResult(
        intent="uncertain",
        confidence=0.5,
        should_ask_explicit_confirmation=True,
        facts_summary=facts_summary,
        analysis_type=analysis.analysis_type,
        rationale=["low_confidence_followup"],
    )
