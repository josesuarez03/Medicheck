from __future__ import annotations

import json
import logging
from typing import Any

try:
    import boto3
    from botocore.exceptions import ClientError
except Exception:  # pragma: no cover
    boto3 = None
    ClientError = Exception

from config.config import Config


logger = logging.getLogger(__name__)
TARGET_MAX_INPUT_TOKENS = 1200
SYSTEM_PROMPT_COMPACT = (
    "Eres Hipo, asistente de triaje médico inicial. "
    "No diagnosticas ni prescribes. "
    "Responde breve, clara y prudentemente. "
    "Prioriza seguridad, urgencia, duración, intensidad y banderas rojas. "
    "Haz como máximo 1 o 2 preguntas si faltan datos."
)


def estimate_tokens(text: str) -> int:
    return max(1, int(len((text or "").strip()) / 4))


def _compact_postgres_context(postgres_context: dict[str, Any]) -> str:
    if not isinstance(postgres_context, dict):
        return ""
    keys = ("allergies", "medications", "medical_history", "ocupacion", "medical_context")
    compact = {key: postgres_context.get(key) for key in keys if postgres_context.get(key)}
    profile = postgres_context.get("profile")
    if isinstance(profile, dict):
        compact["profile"] = {k: profile.get(k) for k in ("age", "sex", "name") if profile.get(k)}
    return json.dumps(compact, ensure_ascii=False)


def build_turn_prompt(context_bundle: dict[str, Any], initial_prompt: str | None = None) -> dict[str, Any]:
    sections: list[tuple[str, str]] = []
    system_prompt = SYSTEM_PROMPT_COMPACT if not initial_prompt else f"{SYSTEM_PROMPT_COMPACT}\n{initial_prompt}"
    sections.append(("system_compact", system_prompt))

    user_input = str(context_bundle.get("user_input") or "").strip()
    sections.append(("turn_input", f"Mensaje actual del paciente: {user_input}"))

    facts_summary = context_bundle.get("facts_summary", {}) or {}
    if facts_summary:
        sections.append(("turn_facts", "Hechos clínicos del turno: " + json.dumps(facts_summary, ensure_ascii=False)))

    postgres_context = _compact_postgres_context(context_bundle.get("postgres_context", {}) or {})
    if postgres_context:
        sections.append(("patient_profile", "Contexto persistente relevante: " + postgres_context))

    recent_turns = context_bundle.get("recent_turns", []) or []
    if recent_turns:
        latest_turns = recent_turns[-2:]
        rendered = []
        for turn in latest_turns:
            user_msg = turn.get("user_message", "")
            assistant_msg = turn.get("assistant_message", "")
            rendered.append(f"Paciente: {user_msg}")
            if assistant_msg:
                rendered.append(f"Asistente: {assistant_msg}")
        sections.append(("recent_turns", "\n".join(rendered)))

    semantic_context = (context_bundle.get("semantic_context", []) or [])[:2]
    if semantic_context:
        rendered = [item.get("text", "") for item in semantic_context if item.get("text")]
        if rendered:
            sections.append(("retrieved_memory", "Memoria relevante: " + " || ".join(rendered)))

    global_semantic_context = (context_bundle.get("global_semantic_context", []) or [])[:2]
    if global_semantic_context:
        rendered = [item.get("text", "") for item in global_semantic_context if item.get("text")]
        if rendered:
            sections.append(("global_memory", "Memoria longitudinal: " + " || ".join(rendered)))

    questions_selected = (context_bundle.get("questions_selected", []) or [])[:2]
    if questions_selected:
        sections.append(("questions", "Preguntas pendientes: " + " | ".join(questions_selected)))

    section_priority = ["global_memory", "retrieved_memory", "recent_turns", "questions"]
    while True:
        prompt_text = "\n\n".join(section_text for _, section_text in sections if section_text.strip())
        used_estimate = estimate_tokens(prompt_text)
        if used_estimate <= TARGET_MAX_INPUT_TOKENS:
            return {
                "prompt": prompt_text,
                "prompt_sections_used": [name for name, _ in sections],
                "prompt_token_budget": {
                    "target_max_input_tokens": TARGET_MAX_INPUT_TOKENS,
                    "used_estimate": used_estimate,
                },
            }
        removable_name = next((name for name in section_priority if any(name == current for current, _ in sections)), None)
        if removable_name is None:
            return {
                "prompt": prompt_text,
                "prompt_sections_used": [name for name, _ in sections],
                "prompt_token_budget": {
                    "target_max_input_tokens": TARGET_MAX_INPUT_TOKENS,
                    "used_estimate": used_estimate,
                },
            }
        sections = [item for item in sections if item[0] != removable_name]


def call_claude(prompt, triage_level=None, max_tokens=400, temperature=0.1, initial_prompt=None):
    if boto3 is None:
        raise RuntimeError("boto3 no está disponible en este entorno.")

    client = boto3.client(service_name="bedrock-runtime", region_name=Config.AWS_REGION)
    model_id = Config.BEDROCK_CLAUDE_INFERENCE_PROFILE_ID or Config.BEDROCK_CLAUDE_MODEL_ID
    if not model_id:
        raise ValueError("Falta configuración Bedrock: define un model ID o inference profile.")

    if isinstance(prompt, dict):
        prompt_payload = build_turn_prompt(prompt, initial_prompt=initial_prompt)
        formatted_prompt = prompt_payload["prompt"]
    else:
        formatted_prompt = str(prompt)
        if initial_prompt:
            formatted_prompt = f"{SYSTEM_PROMPT_COMPACT}\n{initial_prompt}\n{formatted_prompt}"
    if triage_level:
        formatted_prompt += f"\n\nNivel de triaje actual: {triage_level}"

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": formatted_prompt}],
        }
    )

    try:
        response = client.invoke_model(modelId=model_id, body=body, contentType="application/json")
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
    except ClientError as exc:
        err = (exc.response or {}).get("Error", {})
        code = err.get("Code", "")
        message = err.get("Message", "")
        if code == "ValidationException" and "on-demand throughput isn’t supported" in message and not Config.BEDROCK_CLAUDE_INFERENCE_PROFILE_ID:
            raise RuntimeError(
                "El modelo configurado requiere Inference Profile. Configura BEDROCK_CLAUDE_INFERENCE_PROFILE_ID."
            ) from exc
        logger.error("Can't invoke '%s'. Reason: %s", model_id, exc)
        raise
    except Exception as exc:
        logger.error("Can't invoke '%s'. Reason: %s", model_id, exc)
        raise
