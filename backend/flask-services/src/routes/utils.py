"""Helpers de capa routes.

Incluye utilidades de serialización y extracción de token de cabecera.
También expone compatibilidad temporal para objetos migrados a services.
"""

from datetime import datetime

from services.auth.auth import get_user_id_token
from services.chatbot.application.chat_turn_service import process_message_logic
from services.chatbot.application.conversation_service import conversational_dataset_manager


def serialize_timestamp(value):
    """Serializa timestamps sin romper si ya vienen como string desde Redis."""
    if value is None:
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def serialize_conversation_doc(conversation):
    if not isinstance(conversation, dict):
        return conversation
    serialized = dict(conversation)
    if "_id" in serialized:
        serialized["_id"] = str(serialized["_id"])
    for key in ("timestamp", "archived_at", "deleted_at", "purge_after"):
        if key in serialized:
            serialized[key] = serialize_timestamp(serialized.get(key))
    return serialized


def extract_bearer_token(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    if not auth_header.lower().startswith("bearer "):
        return None
    return auth_header.split(" ", 1)[1]


def resolve_request_user_id(
    request,
    allow_query_fallback: bool = False,
    allow_body_fallback: bool = False,
    default_user_id: str | None = None,
):
    user_id = get_user_id_token(request)
    if not user_id and allow_query_fallback:
        user_id = request.args.get("user_id")
    if not user_id and allow_body_fallback:
        payload = request.get_json(silent=True) or {}
        user_id = payload.get("user_id")
    if not user_id and default_user_id is not None:
        user_id = default_user_id
    return user_id


__all__ = [
    "conversational_dataset_manager",
    "extract_bearer_token",
    "process_message_logic",
    "resolve_request_user_id",
    "serialize_conversation_doc",
    "serialize_timestamp",
]
