from services.chatbot.comprehend_medical import detect_entities
from services.chatbot.duration_utils import extract_duration_text
from services.chatbot.pain_utils import extract_pain_scale
import re

PAIN_SCALE_QUESTION = "En una escala del 1 al 10, ¿qué tan intenso es el dolor ahora?"


def _extract_pain_level_reported(text):
    return extract_pain_scale(text)


def _extract_symptom_duration(text):
    return extract_duration_text(text)


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
        full_name = (
            profile.get("name")
            or profile.get("full_name")
            or profile.get("nombre")
            or profile.get("display_name")
        )
        if not full_name:
            first_name = profile.get("first_name") or profile.get("nombre")
            last_name = profile.get("last_name") or profile.get("apellido")
            parts = [part for part in [first_name, last_name] if isinstance(part, str) and part.strip()]
            if parts:
                full_name = " ".join(parts)
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


def init_context(text, user_data=None, existing_context=None):
    entities = detect_entities(text)

    context = existing_context.copy() if isinstance(existing_context, dict) else {
        "name": None,
        "age": None,
        "sex": None,
        "location": None,
        "occupation": None,
        "hobbies": None,
        "lifestyle": None,
        "chief_complaint": None,
        "symptom_duration": None,
        "pain_level_reported": None,
        "red_flags_checked": None,
        "current_medications": None,
        "known_allergies": None,
        "medical_history_known": None
    }

    # Merge with provided user_data if available
    if user_data and isinstance(user_data, dict):
        context.update(user_data)
    _hydrate_profile_demographics(context, user_data)

    # Extract entities detected from text
    if entities:
        for entity in entities:
            if isinstance(entity, dict):
                if entity.get("Category") == "PERSONAL_IDENTIFIABLE_INFORMATION":
                    if entity.get("Type") == "NAME":
                        if context.get("name") in (None, "", [], {}):
                            context["name"] = entity.get("Text")
                elif entity.get("Category") == "PROTECTED_HEALTH_INFORMATION":
                    if entity.get("Type") == "AGE":
                        if context.get("age") in (None, "", [], {}):
                            context["age"] = entity.get("Text")
                    elif entity.get("Type") == "GENDER":
                        if context.get("sex") in (None, "", [], {}):
                            context["sex"] = entity.get("Text")

    if text and not context.get("chief_complaint"):
        context["chief_complaint"] = text.strip()

    # Infer structured answers from free text so asked questions are not repeated
    if context.get("symptom_duration") in (None, "", [], {}):
        duration = _extract_symptom_duration(text)
        if duration:
            context["symptom_duration"] = duration

    if context.get("pain_level_reported") in (None, "", [], {}):
        pain_value = _extract_pain_level_reported(text)
        if pain_value is not None:
            context["pain_level_reported"] = pain_value

    if context.get("red_flags_checked") in (None, "", [], {}):
        red_flags = _extract_red_flags_answer(text)
        if red_flags:
            context["red_flags_checked"] = red_flags

    return {
        "context": context,
        "missing_questions": [],
        "missing_question_meta": [],
        "entities": entities
    }
