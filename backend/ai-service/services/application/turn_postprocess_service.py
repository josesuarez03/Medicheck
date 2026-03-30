import logging
import uuid
from typing import Any, Dict, List

from services.chatbot.conversation_context_service import ConversationContextService
from services.process_data.etl_runner import clear_inactivity_timer, enqueue_etl_run, schedule_inactivity_etl

logger = logging.getLogger(__name__)
conversation_context_service = ConversationContextService()


def _handle_etl(
    user_id: str,
    conversation_id: str | None,
    jwt_token: str | None,
    etl_triggered: bool,
    etl_reasons: List[str],
) -> Dict[str, Any]:
    etl_payload = {
        "triggered": False,
        "status": "not_triggered",
        "reasons": [],
        "run_id": "",
    }

    if etl_triggered and conversation_id:
        run_id = str(uuid.uuid4())
        try:
            clear_inactivity_timer(user_id, conversation_id)
            enqueue_etl_run(
                user_id=user_id,
                conversation_id=conversation_id,
                jwt_token=jwt_token,
                reasons=etl_reasons,
                run_id=run_id,
            )
            etl_payload = {
                "triggered": True,
                "status": "queued",
                "reasons": etl_reasons,
                "run_id": run_id,
            }
        except Exception as e:
            logger.error(
                "No se pudo encolar ETL para conversación %s del usuario %s: %s",
                conversation_id,
                user_id,
                str(e),
            )
    elif conversation_id:
        try:
            schedule_inactivity_etl(user_id=user_id, conversation_id=conversation_id, jwt_token=jwt_token)
        except Exception as e:
            logger.warning(
                "No se pudo programar timeout ETL por inactividad para conversación %s usuario %s: %s",
                conversation_id,
                user_id,
                str(e),
            )

    return etl_payload


def _append_contextual_memory(
    user_id: str,
    conversation_id: str | None,
    current_conversation: Dict[str, Any] | None,
    user_message: str,
    response_data: Dict[str, Any],
    questions_selected: List[str],
    response_source: str,
    expert_meta: Dict[str, Any],
    hybrid_state: Dict[str, Any],
    decision_flags: Dict[str, Any],
) -> None:
    try:
        question_strategy = "single" if len(questions_selected) <= 1 else "dual"
        conversation_context_service.append_turn(
            user_id=user_id,
            conversation_id=conversation_id,
            user_msg=user_message,
            bot_msg=response_data["response"],
            metadata={
                "source_turn_id": len((current_conversation or {}).get("messages", [])) + 1,
                "triaje_level": response_data.get("triaje_level"),
                "symptoms": response_data.get("symptoms"),
                "pain_scale": response_data.get("pain_scale"),
                "questions_selected": questions_selected,
                "answers_detected": bool(user_message and user_message.strip()),
                "question_strategy": question_strategy,
                "response_source": response_source,
                "expert_system": expert_meta,
                "hybrid_state": hybrid_state,
                "decision_flags": decision_flags,
            },
        )
    except Exception as e:
        logger.warning("No se pudo actualizar memoria contextual de embeddings: %s", e)


def handle_turn_postprocess(
    user_id: str,
    conversation_id: str | None,
    jwt_token: str | None,
    etl_triggered: bool,
    etl_reasons: List[str],
    current_conversation: Dict[str, Any] | None,
    user_message: str,
    response_data: Dict[str, Any],
    questions_selected: List[str],
    response_source: str,
    expert_meta: Dict[str, Any],
    hybrid_state: Dict[str, Any],
    decision_flags: Dict[str, Any],
) -> Dict[str, Any]:
    etl_payload = _handle_etl(
        user_id=user_id,
        conversation_id=conversation_id,
        jwt_token=jwt_token,
        etl_triggered=etl_triggered,
        etl_reasons=etl_reasons,
    )
    _append_contextual_memory(
        user_id=user_id,
        conversation_id=conversation_id,
        current_conversation=current_conversation,
        user_message=user_message,
        response_data=response_data,
        questions_selected=questions_selected,
        response_source=response_source,
        expert_meta=expert_meta,
        hybrid_state=hybrid_state,
        decision_flags=decision_flags,
    )
    return etl_payload
