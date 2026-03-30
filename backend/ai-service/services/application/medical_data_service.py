import uuid
from datetime import datetime

from services.chatbot.application.conversation_service import conversation_service
from services.process_data.etl_runner import execute_etl_once


def process_medical_data_for_conversation(
    user_id: str,
    conversation_id: str,
    jwt_token: str | None = None,
    django_api_url: str | None = None,
):
    run_id = str(uuid.uuid4())
    reasons = ["manual_endpoint"]
    queued_time = datetime.utcnow().isoformat()
    conversation_service.update_etl_state(
        user_id,
        conversation_id,
        {
            "last_status": "queued",
            "attempts": 0,
            "last_run_id": run_id,
            "last_reasons": reasons,
            "last_error": "",
            "last_attempt_at": queued_time,
        },
    )
    conversation_service.update_etl_state(
        user_id,
        conversation_id,
        {
            "last_status": "running",
            "attempts": 1,
            "last_run_id": run_id,
            "last_reasons": reasons,
            "last_error": "",
            "last_attempt_at": datetime.utcnow().isoformat(),
        },
    )

    etl_result = execute_etl_once(
        user_id=user_id,
        conversation_id=conversation_id,
        jwt_token=jwt_token,
        django_api_url=django_api_url,
    )
    success = bool(etl_result.get("success"))
    medical_data = etl_result.get("medical_data")
    django_response = etl_result.get("django_response")

    if not medical_data or (isinstance(medical_data, dict) and medical_data.get("error")):
        conversation_service.update_etl_state(
            user_id,
            conversation_id,
            {
                "last_status": "failed",
                "attempts": 1,
                "last_run_id": run_id,
                "last_reasons": reasons,
                "last_error": (medical_data or {}).get("error", "No se pudo procesar la conversación."),
                "last_attempt_at": datetime.utcnow().isoformat(),
            },
        )
        return medical_data or {"error": "No se pudo procesar la conversación."}, 400

    if success:
        success_time = datetime.utcnow().isoformat()
        conversation_service.update_etl_state(
            user_id,
            conversation_id,
            {
                "last_status": "success",
                "attempts": 1,
                "last_run_id": run_id,
                "last_reasons": reasons,
                "last_error": "",
                "last_attempt_at": success_time,
                "last_success_at": success_time,
            },
        )
    else:
        conversation_service.update_etl_state(
            user_id,
            conversation_id,
            {
                "last_status": "failed",
                "attempts": 1,
                "last_run_id": run_id,
                "last_reasons": reasons,
                "last_error": str(etl_result.get("error") or "Error desconocido al enviar a backend principal."),
                "last_attempt_at": datetime.utcnow().isoformat(),
            },
        )

    return {
        "success": success,
        "message": "Datos médicos procesados correctamente." if success else "Datos médicos procesados con error de envío.",
        "medical_data": medical_data,
        "django_response": django_response,
    }, 200
