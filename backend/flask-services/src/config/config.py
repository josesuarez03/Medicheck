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
    DJANGO_SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
    JWT_SECRET_ENV = os.getenv("JWT_SECRET_KEY")
    FLASK_API_KEY = os.getenv("FLASK_API_KEY")
    DJANGO_API_URL = os.getenv("DJANGO_API_URL")
    DJANGO_API_URL_FLASK = os.getenv("DJANGO_API_URL_FLASK")
    MONGO_ENCRYPTION_KEY = os.getenv(
        "MONGO_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(hashlib.sha256((SECRET_KEY or "").encode("utf-8")).digest()).decode("utf-8"),
    )

    # Credenciales para Amazon Web Services
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION")
    BEDROCK_EMBEDDING_MODEL_ID = os.getenv("BEDROCK_EMBEDDING_MODEL_ID")
    BEDROCK_CLAUDE_MODEL_ID = os.getenv("BEDROCK_CLAUDE_MODEL_ID")
    BEDROCK_CLAUDE_INFERENCE_PROFILE_ID = os.getenv("BEDROCK_CLAUDE_INFERENCE_PROFILE_ID")

    # Configuración MongoDB - usar nombres de host de Docker si estamos en contenedores
    MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
    MONGO_PORT = _as_int(os.getenv("MONGO_PORT"), 27017)
    MONGO_DB = os.getenv("MONGO_INITDB_DATABASE", "DB")
    MONGO_USER = os.getenv("MONGO_INITDB_ROOT_USERNAME")
    MONGO_PASS = os.getenv("MONGO_INITDB_ROOT_PASSWORD")

    # Configuración Redis - usar nombres de host de Docker si estamos en contenedores
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = _as_int(os.getenv("REDIS_PORT"), 6379)
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    REDIS_USE_TLS = os.getenv("REDIS_USE_TLS", "False").strip().lower() in {"1", "true", "yes", "on"}
    REDIS_SSL_CERT_REQS = os.getenv("REDIS_SSL_CERT_REQS", "required").strip().lower()
    REDIS_DB = _as_int(os.getenv("REDIS_DB"), 0)
    CHAT_REDIS_DB_CONTEXT = _as_int(os.getenv("CHAT_REDIS_DB_CONTEXT"), 2)
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
    DJANGO_INTEGRATION = os.getenv("DJANGO_INTEGRATION", "False") == "True"

    # Configuraciones de logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')

    @classmethod
    def validate(cls):
        if cls.JWT_SECRET_ENV and (
            (cls.DJANGO_SECRET_KEY and cls.JWT_SECRET_ENV != cls.DJANGO_SECRET_KEY)
            or (cls.SECRET_KEY and cls.JWT_SECRET_ENV != cls.SECRET_KEY)
        ):
            logger.warning(
                "JWT_SECRET_KEY esta configurada y se usara como clave dedicada para validar JWT."
            )

        required_vars = {
            "FLASK_API_KEY": cls.FLASK_API_KEY,
            "REDIS_PASSWORD": cls.REDIS_PASSWORD,
            "REDIS_HOST": cls.REDIS_HOST,
            "REDIS_PORT": cls.REDIS_PORT,
            "SECRET_KEY": cls.SECRET_KEY,
            "MONGO_ENCRYPTION_KEY": cls.MONGO_ENCRYPTION_KEY,
            "JWT_ALGORITHM": cls.JWT_ALGORITHM,
            "MONGO_HOST": cls.MONGO_HOST,
            "MONGO_PORT": cls.MONGO_PORT,
            "MONGO_DB": cls.MONGO_DB,
            "MONGO_INITDB_ROOT_USERNAME": cls.MONGO_USER,
            "MONGO_INITDB_ROOT_PASSWORD": cls.MONGO_PASS,
        }
        missing = [name for name, value in required_vars.items() if value in (None, "", 0)]
        if missing:
            raise EnvironmentError(
                f"Variables de entorno requeridas ausentes o vacias: {', '.join(sorted(missing))}"
            )
        try:
            from cryptography.fernet import Fernet

            Fernet(cls.MONGO_ENCRYPTION_KEY.encode("utf-8"))
        except Exception as exc:
            raise EnvironmentError("MONGO_ENCRYPTION_KEY no es una clave Fernet valida.") from exc
