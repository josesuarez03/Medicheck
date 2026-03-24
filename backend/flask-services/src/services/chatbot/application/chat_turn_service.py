import logging
import json
from datetime import datetime
from typing import List

from config.config import Config
from services.api.send_api import get_patient_global_context
from services.chatbot.application.chat_turn_helpers import (
    _append_missing_questions_to_response,
    _build_progress_fallback_response,
    _build_expert_response_data,
    _compact_llm_guidance,
    _expert_state_payload,
    _extract_prior_state,
    _extract_questions,
    _extract_turn_number,
    _hydrate_profile_demographics,
    _max_triage_level,
    _merge_questions,
    _normalize_triage,
)
from services.chatbot.application.controller_service import decide_controller_mode, normalize_prior_controller_mode
from services.chatbot.application.conversation_service import conversational_dataset_manager
from services.chatbot.application.finalization_service import detect_finalization
from services.chatbot.application.pain_policy_service import apply_pain_question_policy, resolve_pain_state
from services.chatbot.application.turn_persistence_service import persist_turn_data
from services.chatbot.application.turn_postprocess_service import handle_turn_postprocess
from services.expert_system.fallback_adapter import FallbackModelAdapter
from services.expert_system.orchestrator import ExpertOrchestrator

# Configurar logger
logger = logging.getLogger(__name__)


def _has_actionable_llm_output(candidate):
    if not isinstance(candidate, dict):
        return False

    response_text = candidate.get("response")
    if isinstance(response_text, str) and response_text.strip():
        return True

    if _extract_questions(candidate):
        return True

    missing_questions = candidate.get("missing_questions", [])
    return isinstance(missing_questions, list) and any(
        isinstance(question, str) and question.strip() for question in missing_questions
    )

# Singleton para orquestación
expert_orchestrator = ExpertOrchestrator()
fallback_model_adapter = FallbackModelAdapter()

# Prompt inicial compartido
INITIAL_PROMPT = """Eres Hipo, un asistente virtual especializado exclusivamente en triaje médico inicial. Tu función es estrictamente relacionada con la salud y tienes las siguientes responsabilidades y limitaciones:

                ## TUS RESPONSABILIDADES:
                - Realizar un triaje inicial sistemático, solicitando información sobre síntomas, duración, intensidad y factores agravantes/atenuantes.
                - Proporcionar información médica basada en evidencia sobre condiciones y síntomas.
                - Evaluar el nivel de urgencia según los síntomas descritos (emergencia, urgente, puede esperar).
                - Sugerir cuándo buscar atención médica inmediata, urgente o programada.
                - Ofrecer orientaciones generales de autocuidado para síntomas leves.
                - Mantener un registro estructurado de la información proporcionada por el paciente.
                - Identificar posibles "banderas rojas" que requieran atención médica inmediata.

                ## TUS LIMITACIONES:
                - NO puedes diagnosticar condiciones médicas específicas, solo sugerir posibilidades.
                - NO puedes recetar medicamentos ni dosis específicas bajo ninguna circunstancia.
                - NO puedes interpretar resultados de laboratorio o estudios de imagen.
                - NO puedes responder a preguntas no relacionadas con la salud; en esos casos responderás: "Lo siento, mi función se limita exclusivamente a asuntos relacionados con la salud. No puedo responder a preguntas sobre [tema]."
                - NO puedes sustituir la atención médica profesional.

                ## TU PROCESO DE TRIAJE:
                1. Saluda e identifícate como Hipo
                2. Solicita información inicial sobre el motivo de consulta
                3. Realiza preguntas específicas para completar la información:
                - Síntomas principales y secundarios
                - Tiempo de evolución
                - Factores que empeoran o mejoran los síntomas
                - Antecedentes médicos relevantes
                - Medicamentos actuales
                4. Evalúa nivel de urgencia
                5. Proporciona información educativa sobre la posible condición
                6. Ofrece recomendaciones de acción basadas en la urgencia
                7. Documenta la información para futuras referencias

                ## EN CADA INTERACCIÓN:
                - Usa lenguaje claro, preciso y comprensible para personas sin formación médica
                - Mantén un tono profesional pero empático
                - Solicita detalles adicionales cuando la información sea insuficiente
                - Prioriza la seguridad del paciente en todo momento
                - Aclara que tus recomendaciones son orientativas y no reemplazan la consulta médica
                - No hagas listas largas de preguntas.
                - Haz máximo 1 o 2 preguntas por respuesta.
                - Si faltan varios datos, prioriza y pregunta por turnos.
                - Mantén respuestas breves (2-5 líneas).

                Recuerda que tu propósito es orientar hacia la atención médica adecuada, no sustituirla.
                """
def process_message_logic(user_id, user_message, user_data, conversation_id, jwt_token=None):
    if not user_message.strip():
        return {"error": "El mensaje no puede estar vacío."}, 400

    incoming_context = user_data or {}
    postgres_context = {}
    if jwt_token:
        postgres_context = get_patient_global_context(jwt_token=jwt_token)
        profile = postgres_context.get("profile", {}) if isinstance(postgres_context, dict) else {}
        if isinstance(profile, dict):
            incoming_context = {**incoming_context, "patient_profile": profile}

    current_conversation = None
    if conversation_id:
        try:
            current_conversation = conversational_dataset_manager.get_conversation(
                user_id, conversation_id, include_deleted=True
            )
        except Exception:
            current_conversation = None

    if conversation_id and not current_conversation:
        return {
            "error": "Conversación no encontrada.",
            "error_code": "conversation_not_found",
        }, 404

    if isinstance(current_conversation, dict):
        lifecycle_status = str(current_conversation.get("lifecycle_status") or "").strip().lower()
        if lifecycle_status == "deleted":
            return {
                "error": "La conversación fue eliminada.",
                "error_code": "conversation_deleted",
            }, 404
        if lifecycle_status == "archived":
            logger.info(
                "chat_message_blocked_archived %s",
                json.dumps(
                    {
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "lifecycle_status_prev": "archived",
                        "lifecycle_status_next": "archived",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    ensure_ascii=False,
                ),
            )
            return {
                "error": "conversation_archived: esta conversación está archivada. Recupérala para continuar.",
                "error_code": "conversation_archived",
            }, 409

    prior_context, prior_expert_state, prior_hybrid_state, prior_pain = _extract_prior_state(current_conversation)
    existing_context = _hydrate_profile_demographics({**prior_context, **incoming_context}, postgres_context)
    turn_number = _extract_turn_number(current_conversation)

    expert_decision = expert_orchestrator.evaluate(
        user_message=user_message,
        prior_expert_state=prior_expert_state,
    )
    expert_state = _expert_state_payload(expert_decision)
    expert_response_data = _build_expert_response_data(expert_decision, existing_context, expert_state)

    llm_response_data = None
    try:
        llm_candidate = fallback_model_adapter.respond(
            user_message=user_message,
            user_data=user_data,
            initial_prompt=INITIAL_PROMPT,
            user_id=user_id,
            conversation_id=conversation_id,
            existing_context=existing_context,
            postgres_context=postgres_context,
        )
        if isinstance(llm_candidate, dict) and "error" not in llm_candidate and _has_actionable_llm_output(llm_candidate):
            llm_response_data = llm_candidate
        elif isinstance(llm_candidate, dict) and "error" not in llm_candidate:
            logger.warning("Fallback LLM candidate returned no actionable response or questions.")
        elif isinstance(llm_candidate, dict) and llm_candidate.get("error"):
            logger.warning("Fallback LLM candidate returned error: %s", llm_candidate.get("error"))
    except Exception as e:
        logger.warning("Fallback LLM candidate failed: %s", e)

    triage_expert = _normalize_triage(expert_response_data.get("triaje_level"))
    triage_llm = _normalize_triage((llm_response_data or {}).get("triaje_level")) if llm_response_data else triage_expert
    triage_final = _max_triage_level(triage_expert, triage_llm)

    prior_controller_mode = normalize_prior_controller_mode(prior_hybrid_state)
    expert_guard_applied = False

    controller_mode, owner, decision_reasons, expert_action, triage_final = decide_controller_mode(
        expert_decision=expert_decision,
        llm_response_data=llm_response_data,
        triage_final=triage_final,
    )

    if controller_mode in {"emergency_combined", "expert_primary", "expert_fallback"}:
        selected = expert_response_data
    else:
        selected = llm_response_data if llm_response_data else expert_response_data

    pain_scale, explicit_pain, prior_reported_pain, pain_reported = resolve_pain_state(
        user_message=user_message,
        existing_context=existing_context,
        prior_pain=prior_pain,
        expert_response_data=expert_response_data,
        llm_response_data=llm_response_data,
    )

    context_base = existing_context if isinstance(existing_context, dict) else {}
    selected_context = selected.get("context", {})
    if not isinstance(selected_context, dict):
        selected_context = {}
    context_final = {**context_base, **selected_context}
    context_final["pain_scale"] = pain_scale
    context_final["pain_level"] = pain_scale
    if explicit_pain is not None:
        context_final["pain_level_reported"] = explicit_pain
    elif prior_reported_pain is not None:
        context_final["pain_level_reported"] = prior_reported_pain

    conversation_state = selected.get("conversation_state", {})
    if not isinstance(conversation_state, dict):
        conversation_state = {}

    expert_questions = _extract_questions(expert_response_data)
    llm_questions = _extract_questions(llm_response_data)
    max_questions_per_turn = 2
    llm_base_questions = llm_questions[:max_questions_per_turn]

    if controller_mode == "emergency_combined":
        questions_selected = _merge_questions(expert_questions, llm_base_questions, max_questions=max_questions_per_turn)
    elif controller_mode in {"expert_primary", "expert_fallback"}:
        questions_selected = expert_questions[:max_questions_per_turn]
    else:
        questions_selected = llm_base_questions

    questions_selected, pain_asked_now, pain_must_ask, decision_reasons = apply_pain_question_policy(
        current_conversation=current_conversation,
        questions_selected=questions_selected,
        turn_number=turn_number,
        pain_reported=pain_reported,
        decision_reasons=decision_reasons,
        max_questions_per_turn=max_questions_per_turn,
    )

    conversation_state["questions_selected"] = questions_selected
    conversation_state["expert_state"] = expert_state
    if controller_mode in {"expert_primary", "expert_fallback"}:
        conversation_state["missing_fields"] = [k for k, v in expert_decision.state.required_fields_status.items() if not v]
        conversation_state["collected_fields"] = [k for k, v in expert_decision.state.required_fields_status.items() if v]
        conversation_state["next_intent"] = (
            "collect_missing_data" if expert_decision.action == "ask" else "triage_recommendation"
        )
    elif controller_mode == "emergency_combined":
        conversation_state["next_intent"] = "triage_recommendation"
    elif "next_intent" not in conversation_state:
        conversation_state["next_intent"] = "collect_missing_data"

    response_text = selected.get("response") or expert_response_data.get("response") or ""
    if controller_mode == "emergency_combined":
        expert_emergency_text = expert_response_data.get("response") or response_text
        llm_hint = _compact_llm_guidance((llm_response_data or {}).get("response", ""))
        if llm_hint:
            response_text = f"{expert_emergency_text}\n\nOrientación adicional: {llm_hint}"
        else:
            response_text = expert_emergency_text
    if not response_text.strip():
        if questions_selected:
            if len(questions_selected) == 1:
                response_text = f"Para continuar:\n{questions_selected[0]}"
            else:
                response_text = f"Para continuar:\n1. {questions_selected[0]}\n2. {questions_selected[1]}"
        else:
            response_text = _build_progress_fallback_response(
                user_message=user_message,
                current_conversation=current_conversation,
                context_final=context_final,
            )
    elif controller_mode != "emergency_combined":
        response_text = _append_missing_questions_to_response(response_text, questions_selected)

    # If the current turn is still asking for more clinical data, do not mark the
    # conversation as final triage advice yet.
    if questions_selected or "?" in response_text:
        conversation_state["next_intent"] = "collect_missing_data"

    symptoms = selected.get("symptoms", [])
    if not symptoms:
        symptoms = expert_response_data.get("symptoms", [])
    symptoms_pattern = selected.get("symptoms_pattern", {})
    entities = selected.get("entities", [])

    if owner == "llm_primary":
        response_source = "llm"
    elif owner in {"expert_primary", "expert_fallback"}:
        response_source = "expert"
    else:
        response_source = "hybrid"

    controller_source = response_source
    expert_meta = {
        "used": True,
        "case_id": expert_decision.case_id,
        "method_trace": expert_decision.method_trace,
        "confidence": expert_decision.confidence,
        "action": expert_decision.action,
        "rule_ids_applied": expert_decision.rule_ids_applied,
        "fallback_reason": expert_decision.fallback_reason,
        "emergency_triggered": expert_decision.emergency_triggered,
        "controller_source": controller_source,
        "controller_mode": controller_mode,
    }
    decision_flags = {
        "owner": owner,
        "expert_guard_applied": expert_guard_applied,
        "expert_case_id": expert_decision.case_id,
        "expert_action": expert_action,
        "reasons": list(dict.fromkeys(decision_reasons)),
        "turn_number": turn_number,
        "pain": {
            "reported": pain_reported,
            "asked_now": pain_asked_now,
            "must_ask": pain_must_ask,
        },
    }
    hybrid_state = {
        "controller_mode": controller_mode,
        "expert_state": expert_state,
        "last_pain_scale": pain_scale,
        "active_case_locked": False,
        "expert_non_match_streak": 0,
        "last_arbitration": {
            "controller": controller_source,
            "controller_mode_prev": prior_controller_mode,
            "controller_mode_next": controller_mode,
            "triage_expert": triage_expert,
            "triage_llm": triage_llm if llm_response_data else None,
            "triage_final": triage_final,
            "questions_selected_final": questions_selected,
            "decision_owner": owner,
            "decision_reasons": list(dict.fromkeys(decision_reasons)),
            "timestamp": datetime.utcnow().isoformat(),
        },
    }
    prior_etl_state = prior_hybrid_state.get("etl")
    if isinstance(prior_etl_state, dict):
        hybrid_state["etl"] = prior_etl_state

    logger.info(
        "chat_hybrid_turn %s",
        json.dumps(
            {
                "conversation_id": conversation_id,
                "response_source": response_source,
                "case_id": expert_decision.case_id,
                "controller_mode_prev": prior_controller_mode,
                "controller_mode_next": controller_mode,
                "active_case_locked": False,
                "fallback_reason": expert_decision.fallback_reason,
                "takeover_reason": "emergency_detected" if controller_mode == "emergency_combined" else None,
                "handoff_reason": None,
                "expert_non_match_streak": 0,
                "pain_prev": prior_pain,
                "pain_new": pain_scale,
                "triaje_experto": triage_expert,
                "triaje_llm": triage_llm if llm_response_data else None,
                "triaje_final": triage_final,
                "questions_selected_final": questions_selected,
            },
            ensure_ascii=False,
        ),
    )
    if Config.CHAT_DECISION_LOG_FLAGS:
        logger.info(
            "chat_decision_turn %s",
            json.dumps(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "owner": owner,
                    "response_source": response_source,
                    "expert_case_id": expert_decision.case_id,
                    "expert_action": expert_action,
                    "expert_guard_applied": expert_guard_applied,
                    "emergency_triggered": expert_decision.emergency_triggered,
                    "triaje_experto": triage_expert,
                    "triaje_llm": triage_llm if llm_response_data else None,
                    "triaje_final": triage_final,
                    "pain_reported": pain_reported,
                    "pain_asked_now": pain_asked_now,
                    "pain_must_ask": pain_must_ask,
                    "turn_number": turn_number,
                    "decision_reasons": list(dict.fromkeys(decision_reasons)),
                },
                ensure_ascii=False,
            ),
        )
    if llm_response_data and triage_expert != triage_llm:
        logger.warning(
            "chat_hybrid_divergence %s",
            json.dumps(
                {
                    "conversation_id": conversation_id,
                    "case_id": expert_decision.case_id,
                    "triage_expert": triage_expert,
                    "triage_llm": triage_llm,
                    "triage_final": triage_final,
                    "controller": controller_source,
                },
                ensure_ascii=False,
            ),
        )

    response_data = {
        "context": context_final,
        "triaje_level": triage_final,
        "lifecycle_status": "active",
        "entities": entities,
        "response": response_text,
        "symptoms": symptoms,
        "symptoms_pattern": symptoms_pattern,
        "pain_scale": pain_scale,
        "missing_questions": selected.get("missing_questions", []),
        "analysis_type": (
            "hybrid_system"
            if controller_mode == "emergency_combined"
            else selected.get("analysis_type", "expert_system")
        ),
        "conversation_state": conversation_state,
        "decision_flags": decision_flags,
    }
    etl_triggered, etl_reasons = detect_finalization(
        user_message=user_message,
        bot_response=response_text,
        conversation_state=conversation_state,
        triage_level=triage_final,
        controller_mode=controller_mode,
        expert_decision=expert_decision,
        expert_cases=expert_orchestrator.cases,
    )
    conversation_id = persist_turn_data(
        user_id=user_id,
        conversation_id=conversation_id,
        current_conversation=current_conversation,
        user_message=user_message,
        bot_response=response_data["response"],
        response_data=response_data,
        expert_state=expert_state,
        expert_meta=expert_meta,
        hybrid_state=hybrid_state,
    )
    etl_payload = handle_turn_postprocess(
        user_id=user_id,
        conversation_id=conversation_id,
        jwt_token=jwt_token,
        etl_triggered=etl_triggered,
        etl_reasons=etl_reasons,
        current_conversation=current_conversation,
        user_message=user_message,
        response_data=response_data,
        questions_selected=questions_selected,
        response_source=response_source,
        expert_meta=expert_meta,
        hybrid_state=hybrid_state,
        decision_flags=decision_flags,
    )

    return {
        "user_message": user_message,
        "ai_response": response_data["response"],
        "timestamp": datetime.utcnow().isoformat(),
        "analysis": response_data["entities"],
        "context": response_data["context"],
        "symptoms": response_data.get("symptoms", []),
        "symptoms_pattern": response_data.get("symptoms_pattern", {}),
        "pain_scale": response_data.get("pain_scale", 0),
        "lifecycle_status": response_data.get("lifecycle_status", "active"),
        "triaje_level": response_data.get("triaje_level", "Leve"),
        "conversation_state": response_data.get("conversation_state", {}),
        "conversation_id": conversation_id,
        "response_source": response_source,
        "expert_system": expert_meta,
        "decision_flags": decision_flags,
        "etl": etl_payload,
    }, 200

