from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from services.medical_facts import FactsSummary


class TriageResult(BaseModel):
    triage_level: str = "Leve"
    triage_reasons: list[str] = Field(default_factory=list)
    triage_confidence: float = 0.5


class TriageClassification:
    EMERGENCY_MESSAGES = {
        "general": "Tus síntomas podrían requerir valoración urgente. Busca atención médica inmediata.",
        "workplace": "Tus síntomas requieren valoración urgente. Acude al servicio médico de empresa o a urgencias.",
        "educational": "Tus síntomas requieren valoración urgente. Acude al servicio médico del centro o a urgencias.",
    }

    def __init__(self, symptoms: list[str], pain_level: int, environment: str = "general"):
        summary = FactsSummary(symptoms=symptoms, pain_scale=pain_level)
        result = self._classify(summary, existing_context={})
        self.symptoms = symptoms
        self.pain_level = pain_level
        self.environment = environment
        self.triage_level = result.triage_level
        self.triage_reasons = result.triage_reasons
        self.triage_confidence = result.triage_confidence

    @classmethod
    def from_facts(cls, facts_summary: FactsSummary, existing_context: dict[str, Any] | None = None, environment: str = "general") -> "TriageClassification":
        instance = cls(
            symptoms=list(facts_summary.symptoms),
            pain_level=int(facts_summary.pain_scale or 0),
            environment=environment,
        )
        result = cls._classify(facts_summary, existing_context or {})
        instance.triage_level = result.triage_level
        instance.triage_reasons = result.triage_reasons
        instance.triage_confidence = result.triage_confidence
        return instance

    @staticmethod
    def _classify(facts_summary: FactsSummary, existing_context: dict[str, Any]) -> TriageResult:
        reasons: list[str] = []
        score = 0
        pain = int(facts_summary.pain_scale or existing_context.get("pain_level_reported") or 0)
        duration = (facts_summary.duration or "").lower()
        red_flags = {item.lower() for item in facts_summary.red_flags}
        symptoms = {item.lower() for item in facts_summary.symptoms + facts_summary.chief_complaints}
        functional = facts_summary.functional_impact
        history = facts_summary.history + facts_summary.risk_factors

        major_red_flags = {
            "dolor de pecho",
            "dificultad para respirar",
            "disnea",
            "desmayo",
            "convulsiones",
            "sangrado",
            "suicidio",
            "autolesion",
        }
        if red_flags & major_red_flags:
            reasons.extend(sorted(f"red_flag:{flag}" for flag in red_flags & major_red_flags))
            return TriageResult(triage_level="Severo", triage_reasons=reasons, triage_confidence=0.92)

        if ("dolor toracico" in symptoms or "dolor de pecho" in symptoms) and ("disnea" in symptoms or "dificultad para respirar" in red_flags):
            reasons.extend(["combo_chest_pain", "combo_dyspnea"])
            return TriageResult(triage_level="Severo", triage_reasons=reasons, triage_confidence=0.9)
        if ("vomito" in symptoms or "vomitos persistentes" in symptoms) and ("deshidratacion" in symptoms or "deshidratacion" in red_flags):
            reasons.extend(["combo_vomiting", "combo_dehydration"])
            return TriageResult(triage_level="Severo", triage_reasons=reasons, triage_confidence=0.86)
        if ("debilidad" in red_flags or "desmayo" in red_flags) and pain >= 8:
            reasons.extend(["neurologic_red_flag", f"pain_scale_{pain}"])
            return TriageResult(triage_level="Severo", triage_reasons=reasons, triage_confidence=0.88)

        if pain >= 7:
            score += 3
            reasons.append(f"pain_scale_{pain}")
        elif pain >= 4:
            score += 1
            reasons.append(f"pain_scale_{pain}")

        if duration and any(token in duration for token in ("hace", "desde", "dias", "seman", "mes")):
            score += 1
            reasons.append("progressive_duration")

        if functional:
            score += 2
            reasons.append("functional_impact_present")

        if len(symptoms) >= 3:
            score += 2
            reasons.append("multiple_systemic_symptoms")

        if history:
            score += 1
            reasons.append("risk_history_present")

        if score >= 7:
            level = "Severo"
        elif score >= 4:
            level = "Moderado"
        else:
            level = "Leve"
        confidence = min(0.9, 0.45 + (score * 0.06))
        return TriageResult(triage_level=level, triage_reasons=reasons, triage_confidence=round(confidence, 2))

    def classify_triage(self) -> str:
        return self.triage_level

    def handle_severe_case(self, message: str) -> str:
        _ = message
        return self.EMERGENCY_MESSAGES.get(self.environment, self.EMERGENCY_MESSAGES["general"])

    @staticmethod
    def get_workplace_symptoms(category: str = None) -> list[str]:
        lookup = {
            "RESPIRATORY": ["tos", "disnea", "dolor de garganta"],
            "DIGESTIVE": ["nauseas", "vomitos", "dolor abdominal"],
            "NEUROLOGICAL": ["cefalea", "mareo", "desmayo"],
        }
        if category and category in lookup:
            return lookup[category]
        values: list[str] = []
        for symptoms in lookup.values():
            values.extend(symptoms)
        return values

    @staticmethod
    def analyze_symptom_pattern(symptoms: list[str]) -> dict[str, int]:
        pattern = {"RESPIRATORY": 0, "DIGESTIVE": 0, "NEUROLOGICAL": 0, "GENERAL": 0}
        for symptom in symptoms:
            lowered = symptom.lower()
            if any(item in lowered for item in ("tos", "disnea", "garganta")):
                pattern["RESPIRATORY"] += 1
            elif any(item in lowered for item in ("nause", "vomit", "abdominal")):
                pattern["DIGESTIVE"] += 1
            elif any(item in lowered for item in ("mare", "cabeza", "desmayo")):
                pattern["NEUROLOGICAL"] += 1
            else:
                pattern["GENERAL"] += 1
        return pattern
