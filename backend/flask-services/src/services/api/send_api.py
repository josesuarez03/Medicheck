import requests
import logging
import json
import os
import hmac
import hashlib
import time
from config.config import Config

logger = logging.getLogger(__name__)


def _resolve_django_api_url(base_url=None):
    return (
        base_url
        or os.getenv("DJANGO_API_URL_FLASK")
        or os.getenv("DJANGO_API_URL")
        or getattr(Config, "DJANGO_API_URL_FLASK", None)
        or getattr(Config, "DJANGO_API_URL", None)
    )

def _build_url(base_url: str, endpoint: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    ep = endpoint.strip().lstrip("/")
    if base.endswith("/api") and ep.startswith("api/"):
        ep = ep[4:]
    return f"{base}/{ep}"


def _auth_headers(jwt_token=None):
    headers = {"Content-Type": "application/json"}
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"
    return headers


def _canonical_json(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sign_internal_payload(payload, timestamp=None):
    request_timestamp = str(timestamp or int(time.time()))
    canonical_payload = _canonical_json(payload)
    message = f"{request_timestamp}:{canonical_payload}".encode("utf-8")
    signature = hmac.new(
        Config.FLASK_API_KEY.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()
    return request_timestamp, signature


def send_data_to_django(user_id, medical_data, jwt_token=None, base_url=None):

    # URL de la API de Django
    django_api_url = _resolve_django_api_url(base_url)

    endpoint = "api/patients/medical_data_update/"
    url = _build_url(django_api_url, endpoint)
    
    try:
        # Configurar los headers con JWT para autenticación
        headers = _auth_headers(jwt_token=jwt_token)
        
        # Preparar los datos para enviar
        payload = {
            'user_id': user_id,
            'medical_data': medical_data,
            'source': 'chatbot'
        }
        if not jwt_token:
            request_timestamp, signature = _sign_internal_payload(payload)
            headers["X-Request-Timestamp"] = request_timestamp
            headers["X-Request-Signature"] = signature
        
        # Enviar petición POST a la API de Django
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=10  # Timeout de 10 segundos
        )
        # Check if request was successful
        if response.status_code in [200, 201]:
            logger.info(f"Datos enviados correctamente a Django API: {endpoint}")
            return response.json()
        else:
            logger.error(f"Error al enviar datos a Django API: {response.status_code} - {response.text}")
            return {
                "error": f"Error de la API de Django: {response.status_code}",
                "details": response.text
            }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión con Django API: {str(e)}")
        return {"error": f"Error de conexión con la API de Django: {str(e)}"}
    
    except Exception as e:
        logger.error(f"Error inesperado al enviar datos a Django API: {str(e)}")
        return {"error": f"Error inesperado: {str(e)}"}


def get_patient_profile(jwt_token=None):
    django_api_url = _resolve_django_api_url()
    url = _build_url(django_api_url, "patients/me/")
    try:
        response = requests.get(url, headers=_auth_headers(jwt_token=jwt_token), timeout=8)
        if response.status_code == 200:
            return response.json()
        logger.warning("No se pudo recuperar patient profile de Django: %s", response.status_code)
        return {}
    except Exception as e:
        logger.warning("Error recuperando patient profile de Django: %s", str(e))
        return {}


def get_patient_history(jwt_token=None, page_size=5):
    django_api_url = _resolve_django_api_url()
    url = _build_url(django_api_url, f"patients/me/history/?page_size={page_size}")
    try:
        response = requests.get(url, headers=_auth_headers(jwt_token=jwt_token), timeout=8)
        if response.status_code == 200:
            payload = response.json()
            return payload.get("results", payload if isinstance(payload, list) else [])
        logger.warning("No se pudo recuperar patient history de Django: %s", response.status_code)
        return []
    except Exception as e:
        logger.warning("Error recuperando patient history de Django: %s", str(e))
        return []


def get_patient_global_context(jwt_token=None):
    profile = get_patient_profile(jwt_token=jwt_token)
    history = get_patient_history(jwt_token=jwt_token, page_size=5)
    return {
        "profile": profile if isinstance(profile, dict) else {},
        "history": history if isinstance(history, list) else [],
    }
