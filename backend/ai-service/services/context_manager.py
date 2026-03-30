from __future__ import annotations

import re

from services.comprehend_medical import detect_entities
from services.duration_utils import extract_duration_text
from services.medical_facts import ClinicalExtractionResult, FactsSummary
from services.pain_utils import extract_pain_scale


PAIN_SCALE_QUESTION = "En una escala del 1 al 10, ¿qué tan intenso es el dolor ahora?"


def _extract_red_flags_answer(text):
    if not text:
        return None
    lowered = text.strip().lower()
    has_red_flags = re.search(
        r"(dificultad para respirar|dolor de pecho|desmayo|fiebre|convuls|sangrado|debilidad)",
        lowered,
    )
    has_negation = re.search(r"\b(no|ninguno|ninguna|nada|niego|sin)\b", lowered)
    if has_red_flags:
        return "no" if has_negation else "sí"
    return None


def is_pain_scale_question(text):
    if not isinstance(text, str) or not text.strip():
        return False
    lowered = text.strip().lower()
    return (
        "escala del 1 al 10" in lowered
        or ("intenso" in lowered and "dolor" in lowered)
        or ("intensidad" in lowered and "dolor" in lowered)
    )


def has_explicit_pain_report(context):
    if not isinstance(context, dict):
        return False
    value = context.get("pain_level_reported")
    return isinstance(value, int) and 0 <= value <= 10


def _hydrate_profile_demographics(context, user_data):
    if not isinstance(context, dict) or not isinstance(user_data, dict):
        return
    profile = user_data.get("patient_profile", {})
    if not isinstance(profile, dict):
        return
    if context.get("name") in (None, "", [], {}):
        full_name = profile.get("name") or profile.get("full_name") or profile.get("nombre")
        if isinstance(full_name, str) and full_name.strip():
            context["name"] = full_name.strip()
    if context.get("sex") in (None, "", [], {}):
        sex_value = profile.get("sex") or profile.get("gender") or profile.get("sexo")
        if isinstance(sex_value, str) and sex_value.strip():
            context["sex"] = sex_value.strip()
    if context.get("age") in (None, "", [], {}):
        age_value = profile.get("age") or profile.get("edad")
        if isinstance(age_value, (int, str)) and str(age_value).strip():
            context["age"] = age_value


def _facts_summary_from_payload(payload) -> FactsSummary:
    if isinstance(payload, dict):
        summary = payload.get("facts_summary", {})
        if isinstance(summary, dict):
            return FactsSummary(**summary)
    return FactsSummary()


def init_context(text, user_data=None, existing_context=None):
    extraction = detect_entities(text, context=existing_context)
    facts_summary = _facts_summary_from_payload(extraction)
    context = existing_context.copy() if isinstance(existing_context, dict) else {
        "name": None,
        "age": None,
        "sex": None,
        "chief_complaint": None,
        "symptom_duration": None,
        "pain_level_reported": None,
        "red_flags_checked": None,
        "current_medications": None,
        "known_allergies": None,
        "medical_history_known": None,
    }
    if user_data and isinstance(user_data, dict):
        profile = user_data.get("patient_profile")
        if isinstance(profile, dict):
            context["patient_profile"] = profile
    _hydrate_profile_demographics(context, user_data)

    if facts_summary.chief_complaints:
        context["chief_complaint"] = facts_summary.chief_complaints[0]
    elif text and not context.get("chief_complaint"):
        context["chief_complaint"] = text.strip()

    duration = facts_summary.duration or extract_duration_text(text)
    if duration:
        context["symptom_duration"] = duration

    pain_value = facts_summary.pain_scale
    if pain_value is None:
        pain_value = extract_pain_scale(text)
    if pain_value is not None:
        context["pain_level_reported"] = pain_value

    red_flags = facts_summary.red_flags
    if red_flags:
        context["red_flags_checked"] = "sí"
    else:
        red_flags_answer = _extract_red_flags_answer(text)
        if red_flags_answer:
            context["red_flags_checked"] = red_flags_answer

    if facts_summary.medications:
        context["current_medications"] = "; ".join(facts_summary.medications)
    if facts_summary.allergies:
        context["known_allergies"] = "; ".join(facts_summary.allergies)
    if facts_summary.history:
        context["medical_history_known"] = "; ".join(facts_summary.history)

    return {
        "context": context,
        "missing_questions": [],
        "missing_question_meta": [],
        "entities": extraction.get("facts", []),
        "facts_summary": facts_summary.model_dump(),
    }
