from typing import Any, Dict

from services.chatbot.application.conversation_service import conversational_dataset_manager


def persist_turn_data(
    user_id: str,
    conversation_id: str | None,
    current_conversation: Dict[str, Any] | None,
    user_message: str,
    bot_response: str,
    response_data: Dict[str, Any],
    expert_state: Dict[str, Any],
    expert_meta: Dict[str, Any],
    hybrid_state: Dict[str, Any],
) -> str:
    messages = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": bot_response},
    ]

    medical_context = {
        "analysis": response_data["entities"],
        "context_snapshot": response_data.get("context", {}),
        "expert_state": expert_state,
        "expert_trace": expert_meta,
        "hybrid_state": hybrid_state,
    }

    if conversation_id:
        if current_conversation:
            all_messages = current_conversation.get("messages", [])
            all_messages.extend(messages)
            conversational_dataset_manager.update_conversation(
                user_id,
                conversation_id,
                messages=all_messages,
                symptoms=response_data.get("symptoms", []),
                symptoms_pattern=response_data.get("symptoms_pattern", {}),
                pain_scale=response_data.get("pain_scale", 0),
                triaje_level=response_data.get("triaje_level") or None,
                medical_context=medical_context,
            )
        else:
            conversation_id = conversational_dataset_manager.add_conversation(
                user_id,
                medical_context,
                messages,
                response_data.get("symptoms", []),
                response_data.get("symptoms_pattern", {}),
                response_data.get("pain_scale", 0),
                response_data.get("triaje_level") or None,
            )
    else:
        conversation_id = conversational_dataset_manager.add_conversation(
            user_id,
            medical_context,
            messages,
            response_data.get("symptoms", []),
            response_data.get("symptoms_pattern", {}),
            response_data.get("pain_scale", 0),
            response_data.get("triaje_level") or None,
        )

    return conversation_id
