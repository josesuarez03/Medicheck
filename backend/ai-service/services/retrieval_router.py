from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from services.medical_facts import FactsSummary


RetrievalLevel = Literal["cheap", "medium", "full"]


class RetrievalDecision(BaseModel):
    level: RetrievalLevel
    use_summary: bool = False
    summary_only: bool = False
    episodic_top_k: int = 0
    global_top_k: int = 0
    reasons: list[str] = Field(default_factory=list)


class RetrievalRouter:
    @staticmethod
    def decide(
        *,
        clinical_signal_score: float,
        facts_summary: FactsSummary,
        triage_level: str | None,
        analysis_type: str,
        existing_context: dict | None = None,
    ) -> RetrievalDecision:
        existing_context = existing_context or {}
        if analysis_type in {"greeting", "non_clinical"}:
            return RetrievalDecision(level="cheap", reasons=["non_clinical_turn"])

        reasons: list[str] = []
        has_persistent_clinical_context = any(
            existing_context.get(key)
            for key in (
                "known_allergies",
                "medical_history_known",
                "current_medications",
                "chief_complaint",
                "pain_level_reported",
            )
        )
        has_red_flags = bool(facts_summary.red_flags)
        has_high_pain = facts_summary.pain_scale is not None and facts_summary.pain_scale >= 7
        has_core_clinical_facts = bool(
            facts_summary.chief_complaints
            or facts_summary.symptoms
            or facts_summary.medications
            or facts_summary.allergies
            or facts_summary.history
        )

        if has_red_flags or triage_level == "Severo":
            reasons.append("severe_or_red_flags")
            return RetrievalDecision(
                level="full",
                use_summary=True,
                episodic_top_k=2,
                global_top_k=2,
                reasons=reasons,
            )

        if has_high_pain:
            reasons.append("high_pain")
        if has_persistent_clinical_context:
            reasons.append("persistent_context_present")
        if clinical_signal_score >= 0.55:
            reasons.append("high_signal_score")
        if facts_summary.duration:
            reasons.append("duration_present")

        if has_core_clinical_facts and (clinical_signal_score >= 0.55 or has_high_pain or has_persistent_clinical_context):
            return RetrievalDecision(
                level="full",
                use_summary=True,
                episodic_top_k=2,
                global_top_k=2,
                reasons=reasons or ["clinical_full_context"],
            )

        if has_core_clinical_facts or clinical_signal_score >= 0.25:
            return RetrievalDecision(
                level="medium",
                use_summary=True,
                summary_only=not has_core_clinical_facts,
                episodic_top_k=1 if has_core_clinical_facts else 0,
                global_top_k=1 if has_persistent_clinical_context else 0,
                reasons=reasons or ["moderate_signal_context"],
            )

        return RetrievalDecision(level="cheap", reasons=["low_signal_context"])
