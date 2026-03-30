from flask import jsonify, request
import logging
from datetime import datetime
from . import bp
from routes.utils import extract_bearer_token, resolve_request_user_id, serialize_conversation_doc
from services.chatbot.application.chat_turn_service import process_message_logic
from services.chatbot.application.conversation_service import conversation_service
from services.chatbot.application.medical_data_service import process_medical_data_for_conversation

# Configurar logger
logger = logging.getLogger(__name__)

@bp.route('/message', methods=['POST'])
def process_message():

    data = request.get_json()
    user_id = resolve_request_user_id(request)
    if not user_id:
        return jsonify({"error": "Se requiere autenticación válida."}), 401
    
    user_message = data.get('message', '')
    user_data = data.get('context', {})
    conversation_id = data.get('conversation_id', None)
    token = extract_bearer_token(request.headers.get("Authorization"))
    
    result, status_code = process_message_logic(user_id, user_message, user_data, conversation_id, jwt_token=token)
    
    if status_code != 200:
        return jsonify(result), status_code
    
    return jsonify(result), 200

@bp.route('/conversations', methods=['GET'])
def get_user_conversations():
    user_id = resolve_request_user_id(request)
    
    if not user_id:
        return jsonify({"error": "Se requiere autenticación válida."}), 401
    
    try:
        view = request.args.get("view", "active")
        conversations = conversation_service.list_conversations(user_id, view=view)
        conversations = [serialize_conversation_doc(conv) for conv in conversations]
        
        return jsonify({"conversations": conversations})
    except Exception as e:
        logger.error(f"Error al obtener conversaciones: {str(e)}")
        return jsonify({"error": f"Error al obtener conversaciones: {str(e)}"}), 500


@bp.route('/conversations', methods=['DELETE'])
def soft_delete_user_conversations():
    user_id = resolve_request_user_id(request)

    if not user_id:
        return jsonify({"error": "Se requiere autenticación válida."}), 401

    try:
        deleted_count = conversation_service.soft_delete_all(user_id)
        logger.info(
            "chat_conversations_soft_deleted_bulk user_id=%s count=%s timestamp=%s",
            user_id,
            deleted_count,
            datetime.utcnow().isoformat(),
        )
        return jsonify({"success": True, "soft_deleted_count": deleted_count})
    except Exception as e:
        logger.error(f"Error al eliminar conversaciones del usuario {user_id}: {str(e)}")
        return jsonify({"error": f"Error al eliminar conversaciones: {str(e)}"}), 500

@bp.route('/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    user_id = resolve_request_user_id(request)
    
    if not user_id:
        return jsonify({"error": "Se requiere autenticación válida."}), 401
    
    try:
        conversation = conversation_service.get_conversation(user_id, conversation_id)
        if not conversation:
            return jsonify({"error": "Conversación no encontrada."}), 404

        conversation = serialize_conversation_doc(conversation)
        return jsonify({"conversation": conversation})
    except Exception as e:
        logger.error(f"Error al obtener conversación: {str(e)}")
        return jsonify({"error": f"Error al obtener conversación: {str(e)}"}), 500


@bp.route('/conversation/<conversation_id>/archive', methods=['POST'])
def archive_conversation(conversation_id):
    user_id = resolve_request_user_id(request)

    if not user_id:
        return jsonify({"error": "Se requiere autenticación válida."}), 401

    try:
        modified = conversation_service.archive(user_id, conversation_id)
        if not modified:
            return jsonify({"error": "Conversación no encontrada o no se puede archivar."}), 404
        logger.info(
            "chat_conversation_archived user_id=%s conversation_id=%s lifecycle_status_prev=active lifecycle_status_next=archived timestamp=%s",
            user_id,
            conversation_id,
            datetime.utcnow().isoformat(),
        )
        return jsonify({"success": True, "message": "Conversación archivada correctamente."})
    except Exception as e:
        logger.error(f"Error al archivar conversación {conversation_id}: {str(e)}")
        return jsonify({"error": f"Error al archivar conversación: {str(e)}"}), 500


@bp.route('/conversation/<conversation_id>/recover', methods=['POST'])
def recover_conversation(conversation_id):
    user_id = resolve_request_user_id(request)

    if not user_id:
        return jsonify({"error": "Se requiere autenticación válida."}), 401

    try:
        modified = conversation_service.recover(user_id, conversation_id)
        if not modified:
            return jsonify({"error": "Conversación no encontrada o no se puede recuperar."}), 404
        logger.info(
            "chat_conversation_recovered user_id=%s conversation_id=%s lifecycle_status_prev=archived lifecycle_status_next=active timestamp=%s",
            user_id,
            conversation_id,
            datetime.utcnow().isoformat(),
        )
        return jsonify({"success": True, "message": "Conversación recuperada correctamente."})
    except Exception as e:
        logger.error(f"Error al recuperar conversación {conversation_id}: {str(e)}")
        return jsonify({"error": f"Error al recuperar conversación: {str(e)}"}), 500

@bp.route('/conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    user_id = resolve_request_user_id(request)
    
    if not user_id:
        return jsonify({"error": "Se requiere autenticación válida."}), 401
    
    try:
        deleted = conversation_service.soft_delete(user_id, conversation_id)
        if not deleted:
            return jsonify({"error": "Conversación no encontrada o no pudo ser eliminada."}), 404

        logger.info(
            "chat_conversation_soft_deleted user_id=%s conversation_id=%s lifecycle_status_prev=active_or_archived lifecycle_status_next=deleted timestamp=%s",
            user_id,
            conversation_id,
            datetime.utcnow().isoformat(),
        )
        return jsonify({"success": True, "message": "Conversación eliminada correctamente (retención 30 días)."})
    except Exception as e:
        logger.error(f"Error al eliminar conversación: {str(e)}")
        return jsonify({"error": f"Error al eliminar conversación: {str(e)}"}), 500

@bp.route('/sync', methods=['POST'])
def sync_redis_to_mongo():
    user_id = resolve_request_user_id(request)
    
    if not user_id:
        return jsonify({"error": "Se requiere autenticación válida."}), 401
    
    conversation_id = request.get_json().get('conversation_id', None)
    
    try:
        conversation_service.sync_to_mongo(user_id, conversation_id)
        return jsonify({"success": True, "message": "Sincronización completada."})
    except Exception as e:
        logger.error(f"Error en la sincronización: {str(e)}")
        return jsonify({"error": f"Error en la sincronización: {str(e)}"}), 500
    
@bp.route('/process_medical_data', methods=['POST'])
def process_medical_data():

    user_id = resolve_request_user_id(request)
    data = request.get_json()
    
    if not user_id:
        return jsonify({"error": "Se requiere autenticación válida."}), 401
    
    conversation_id = data.get('conversation_id')
    django_api_url = data.get('django_api_url')
    
    if not conversation_id:
        return jsonify({"error": "Se requiere ID de conversación"}), 400
    
    try:
        token = extract_bearer_token(request.headers.get("Authorization"))
        result, status_code = process_medical_data_for_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            jwt_token=token,
            django_api_url=django_api_url,
        )
        return jsonify(result), status_code
    
    except Exception as e:
        logger.error(f"Error al procesar datos médicos: {str(e)}")
        return jsonify({"error": f"Error al procesar datos médicos: {str(e)}"}), 500

