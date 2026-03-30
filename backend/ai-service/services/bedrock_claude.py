import boto3
from botocore.exceptions import ClientError
from config.config import Config
import json
import logging

logger = logging.getLogger(__name__)

def call_claude(prompt, triage_level=None, max_tokens=500, temperature=0.1, initial_prompt=None):

    client = boto3.client(
        service_name='bedrock-runtime', 
        region_name=Config.AWS_REGION
    )

    model_id = Config.BEDROCK_CLAUDE_INFERENCE_PROFILE_ID or Config.BEDROCK_CLAUDE_MODEL_ID
    if not model_id:
        raise ValueError(
            "Falta configuración Bedrock: define BEDROCK_CLAUDE_INFERENCE_PROFILE_ID o BEDROCK_CLAUDE_MODEL_ID."
        )

    # Handle different prompt formats
    if isinstance(prompt, dict):
        # If prompt is a context dict, format it appropriately
        formatted_prompt = _format_context_prompt(prompt, initial_prompt)
    else:
        # If prompt is a string, combine with initial prompt if provided
        formatted_prompt = str(prompt)
        if initial_prompt:
            formatted_prompt = f"{initial_prompt}\n\n{formatted_prompt}"

    # Add triage level context if provided
    if triage_level:
        formatted_prompt += f"\n\nNivel de triaje actual: {triage_level}"

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": formatted_prompt
            }
        ]
    })

    try:
        response = client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json"
        )

        # Process response
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    
    except ClientError as e:
        err = (e.response or {}).get("Error", {})
        code = err.get("Code", "")
        message = err.get("Message", "")

        if (
            code == "ValidationException"
            and "on-demand throughput isn’t supported" in message
            and not Config.BEDROCK_CLAUDE_INFERENCE_PROFILE_ID
        ):
            raise RuntimeError(
                "El modelo configurado requiere Inference Profile. "
                "Configura BEDROCK_CLAUDE_INFERENCE_PROFILE_ID o usa un model ID on-demand soportado."
            ) from e

        logger.error("Can't invoke '%s'. Reason: %s", model_id, e)
        raise
    except Exception as e:
        logger.error("Can't invoke '%s'. Reason: %s", model_id, e)
        raise

def _format_context_prompt(context_dict, initial_prompt=None):

    prompt_parts = []
    
    # Add initial prompt if available
    if initial_prompt:
        prompt_parts.append(initial_prompt)
    
    # Add existing initial prompt from context if available
    if 'initial_prompt' in context_dict and not initial_prompt:
        prompt_parts.append(context_dict['initial_prompt'])
    
    # Add user input
    if 'user_input' in context_dict:
        prompt_parts.append(f"Usuario: {context_dict['user_input']}")

    if context_dict.get("interaction_style"):
        prompt_parts.append(
            "Estilo de interacción:\n"
            f"- interaction_style: {context_dict.get('interaction_style')}\n"
            f"- max_questions_per_turn: {context_dict.get('max_questions_per_turn', 2)}\n"
            f"- intro_mode: {context_dict.get('intro_mode', 'brief_context_plus_one_question')}\n"
            "- No hagas listas largas de preguntas.\n"
            "- Responde de forma breve (2-5 líneas).\n"
            "- Haz máximo 1 o 2 preguntas en este turno."
        )

    if context_dict.get("conversation_summary"):
        prompt_parts.append(f"Resumen acumulado de conversación:\n{context_dict['conversation_summary']}")

    if context_dict.get("recent_turns"):
        recent_lines = []
        for turn in context_dict["recent_turns"]:
            recent_lines.append(f"Paciente: {turn.get('user_message', '')}")
            recent_lines.append(f"Asistente: {turn.get('assistant_message', '')}")
        if recent_lines:
            prompt_parts.append("Últimos turnos relevantes:\n" + "\n".join(recent_lines))

    if context_dict.get("semantic_context"):
        semantic_lines = []
        for item in context_dict["semantic_context"]:
            txt = item.get("text", "")
            score = item.get("score", 0)
            semantic_lines.append(f"[sim={score:.3f}] {txt}")
        if semantic_lines:
            prompt_parts.append("Contexto semántico recuperado:\n" + "\n".join(semantic_lines))

    if context_dict.get("global_semantic_context"):
        global_semantic_lines = []
        for item in context_dict["global_semantic_context"]:
            txt = item.get("text", "")
            score = item.get("score", 0)
            cid = item.get("conversation_id", "")
            global_semantic_lines.append(f"[sim={score:.3f}] ({cid}) {txt}")
        if global_semantic_lines:
            prompt_parts.append("Memoria global del paciente (otras conversaciones):\n" + "\n".join(global_semantic_lines))

    if context_dict.get("global_mongo_context"):
        prompt_parts.append("Resumen global Mongo del paciente:\n" + json.dumps(context_dict["global_mongo_context"], ensure_ascii=False))

    if context_dict.get("postgres_context"):
        prompt_parts.append("Contexto clínico canónico (Postgres/Django):\n" + json.dumps(context_dict["postgres_context"], ensure_ascii=False))
    
    # Add medical context
    if 'medical_entities' in context_dict:
        entities_text = ", ".join([entity.get('Text', '') for entity in context_dict['medical_entities']])
        if entities_text:
            prompt_parts.append(f"Entidades médicas detectadas: {entities_text}")
    
    # Add symptoms if available
    if 'symptoms' in context_dict:
        symptoms_text = ", ".join(context_dict['symptoms'])
        if symptoms_text:
            prompt_parts.append(f"Síntomas identificados: {symptoms_text}")
    
    # Add pain level if available
    if 'pain_level' in context_dict and context_dict['pain_level'] > 0:
        prompt_parts.append(f"Nivel de dolor: {context_dict['pain_level']}/10")
    
    # Add environment context
    if 'environment' in context_dict:
        prompt_parts.append(f"Contexto: {context_dict['environment']}")

    if context_dict.get("questions_selected"):
        prompt_parts.append(
            "Preguntas seleccionadas para este turno:\n"
            + "\n".join(f"- {q}" for q in context_dict["questions_selected"])
        )
    elif context_dict.get("missing_questions"):
        prompt_parts.append(f"Cantidad de datos faltantes: {len(context_dict['missing_questions'])}")
    
    return "\n".join(prompt_parts) if prompt_parts else "Hola, ¿en qué puedo ayudarte?"
