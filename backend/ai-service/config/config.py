from dotenv import load_dotenv
import os
import logging
import base64
import hashlib

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno (solo se usará si no están ya definidas en el entorno)
load_dotenv()


def _as_int(value, default):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


class Config:
    # Configuraciones de la aplicación
    DEBUG = os.getenv('DEBUG') == 'True'
    SECRET_KEY = os.getenv("SECRET_KEY",)
    JWT_SECRET_ENV = os.getenv("JWT_SECRET_KEY")

    # Secreto HMAC de comunicacion interna gateway<->ai-service. Heredado del
    # nombre antiguo FLASK_API_KEY (cuando expert-service era Flask). Ya no es
    # obligatorio en validate(), pero sigue recomendado en produccion.
    INTERNAL_SHARED_SECRET = os.getenv("INTERNAL_SHARED_SECRET") or os.getenv("FLASK_API_KEY")
    FLASK_API_KEY = INTERNAL_SHARED_SECRET  # alias retrocompatible

    # Clave de cifrado de conversaciones (Fernet). Antes MONGO_ENCRYPTION_KEY.
    # Orden de precedencia: CHAT_ENCRYPTION_KEY -> MONGO_ENCRYPTION_KEY (legacy)
    # -> derivada de SECRET_KEY (no recomendado en produccion).
    CHAT_ENCRYPTION_KEY = (
        os.getenv("CHAT_ENCRYPTION_KEY")
        or os.getenv("MONGO_ENCRYPTION_KEY")
        or base64.urlsafe_b64encode(
            hashlib.sha256((SECRET_KEY or "").encode("utf-8")).digest()
        ).decode("utf-8")
    )
    MONGO_ENCRYPTION_KEY = CHAT_ENCRYPTION_KEY  # alias retrocompatible

    # Enfoque dual dentro/fuera de Venezuela.
    DEFAULT_USER_COUNTRY = os.getenv("DEFAULT_USER_COUNTRY", "VE")
    DISASTER_CONTEXT_LABEL = os.getenv(
        "DISASTER_CONTEXT_LABEL",
        "terremoto Venezuela 2026",
    )

    # Credenciales para Amazon Web Services
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION")
    BEDROCK_EMBEDDING_MODEL_ID = os.getenv("BEDROCK_EMBEDDING_MODEL_ID")
    BEDROCK_EMBEDDING_DIMENSIONS = _as_int(os.getenv("BEDROCK_EMBEDDING_DIMENSIONS"), 1024)
    BEDROCK_CLAUDE_MODEL_ID = os.getenv("BEDROCK_CLAUDE_MODEL_ID")
    BEDROCK_CLAUDE_INFERENCE_PROFILE_ID = os.getenv("BEDROCK_CLAUDE_INFERENCE_PROFILE_ID")
    # Limitador de concurrencia hacia Bedrock: acota cuantas invocaciones a
    # Claude corren en paralelo para evitar throttling (429) y controlar costos
    # ante picos de chats simultaneos. El exceso espera brevemente y, si no
    # adquiere turno dentro del timeout, se rechaza con un error claro.
    BEDROCK_MAX_CONCURRENCY = _as_int(os.getenv("BEDROCK_MAX_CONCURRENCY"), 4)
    BEDROCK_ACQUIRE_TIMEOUT_SECONDS = _as_int(os.getenv("BEDROCK_ACQUIRE_TIMEOUT_SECONDS"), 30)

    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT = _as_int(os.getenv("POSTGRES_PORT"), 5432)
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

    # MongoDB eliminado en esta rama (ai-microservices-disaster).

    # Configuración Redis - usar nombres de host de Docker si estamos en contenedores
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = _as_int(os.getenv("REDIS_PORT"), 6379)
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    REDIS_USE_TLS = os.getenv("REDIS_USE_TLS", "False").strip().lower() in {"1", "true", "yes", "on"}
    REDIS_SSL_CERT_REQS = os.getenv("REDIS_SSL_CERT_REQS", "required").strip().lower()
    REDIS_DB = _as_int(os.getenv("REDIS_DB_SESSIONS"), _as_int(os.getenv("REDIS_DB"), 0))
    REDIS_DB_CONVERSATIONS = _as_int(
        os.getenv("REDIS_DB_CONVERSATIONS"),
        _as_int(os.getenv("REDIS_DB_CONTEXT"), 2),
    )
    REDIS_DB_CONTEXT = _as_int(
        os.getenv("REDIS_DB_CONTEXT"),
        _as_int(os.getenv("CHAT_REDIS_DB_CONTEXT"), 2),
    )
    REDIS_DB_EPHEMERAL = _as_int(os.getenv("REDIS_DB_EPHEMERAL"), 6)
    CHAT_REDIS_DB_CONTEXT = REDIS_DB_CONTEXT
    CHAT_CONTEXT_TTL_SECONDS = _as_int(os.getenv("CHAT_CONTEXT_TTL_SECONDS"), 60 * 60 * 24)
    CHAT_CONTEXT_WINDOW_N = _as_int(os.getenv("CHAT_CONTEXT_WINDOW_N"), 8)
    CHAT_CONTEXT_TOP_K = _as_int(os.getenv("CHAT_CONTEXT_TOP_K"), 5)
    CHAT_CONTROLLER_MODE = os.getenv("CHAT_CONTROLLER_MODE", "expert_owner_on_match")
    CHAT_EMERGENCY_MODE = os.getenv("CHAT_EMERGENCY_MODE", "combined")
    CHAT_FORCE_PAIN_BY_TURN = _as_int(os.getenv("CHAT_FORCE_PAIN_BY_TURN"), 2)
    CHAT_EXPERT_GUARD_MAX_QUESTIONS = _as_int(os.getenv("CHAT_EXPERT_GUARD_MAX_QUESTIONS"), 1)
    CHAT_DECISION_LOG_FLAGS = os.getenv("CHAT_DECISION_LOG_FLAGS", "true").strip().lower() in {"1", "true", "yes", "on"}

    # Usar una clave dedicada para JWT; si no existe, mantener compatibilidad hacia atras.
    JWT_SECRET = JWT_SECRET_ENV
    JWT_SECRET_KEY = JWT_SECRET
    JWT_ALGORITHM =  os.getenv("JWT_ALGORITHM")

    # Configuraciones de logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')

    @classmethod
    def validate(cls):
        if cls.JWT_SECRET_ENV and cls.SECRET_KEY and cls.JWT_SECRET_ENV != cls.SECRET_KEY:
            logger.warning(
                "JWT_SECRET_KEY esta configurada y se usara como clave dedicada para validar JWT."
            )

        if not cls.INTERNAL_SHARED_SECRET:
            logger.warning(
                "INTERNAL_SHARED_SECRET/FLASK_API_KEY no configurado; la comunicacion "
                "interna gateway<->ai-service no podra validarse por HMAC."
            )

        required_vars = {
            "REDIS_PASSWORD": cls.REDIS_PASSWORD,
            "REDIS_HOST": cls.REDIS_HOST,
            "REDIS_PORT": cls.REDIS_PORT,
            "SECRET_KEY": cls.SECRET_KEY,
            "CHAT_ENCRYPTION_KEY": cls.CHAT_ENCRYPTION_KEY,
            "JWT_ALGORITHM": cls.JWT_ALGORITHM,
        }
        missing = [name for name, value in required_vars.items() if value in (None, "", 0)]
        if missing:
            raise EnvironmentError(
                f"Variables de entorno requeridas ausentes o vacias: {', '.join(sorted(missing))}"
            )
        try:
            from cryptography.fernet import Fernet

            Fernet(cls.CHAT_ENCRYPTION_KEY.encode("utf-8"))
        except Exception as exc:
            raise EnvironmentError("CHAT_ENCRYPTION_KEY no es una clave Fernet valida.") from exc
