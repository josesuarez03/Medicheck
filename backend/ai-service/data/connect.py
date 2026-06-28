"""Conexiones de datos para ai-service.

En esta rama (ai-microservices-disaster) MongoDB fue eliminado. Este modulo
expone las conexiones Redis reales que reemplazan el almacenamiento de
conversaciones activas y de contexto, siguiendo el mismo patron de conexion
que `gateway/services/ws_session.py` (timeouts cortos, no rompe si Redis no
responde al primer ping).

`mongo_db` se mantiene como `None` para que cualquier codigo legado que lo
importe con manejo defensivo (try/except o chequeo `is not None`) siga
funcionando sin romper.
"""

import logging
import os

import redis

logger = logging.getLogger(__name__)


def _as_int(value, default):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = _as_int(os.getenv("REDIS_PORT"), 6379)
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB_CONVERSATIONS = _as_int(
    os.getenv("REDIS_DB_CONVERSATIONS"),
    _as_int(os.getenv("REDIS_DB_CONTEXT"), 2),
)
REDIS_DB_CONTEXT = _as_int(os.getenv("REDIS_DB_CONTEXT"), 2)


def _build_client(db: int) -> redis.Redis:
    """Crea un cliente Redis con timeouts cortos.

    `decode_responses=False` (bytes) porque `RedisCacheManager` decodifica
    explicitamente los miembros del set con `.decode('utf-8')`.
    """
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=db,
        decode_responses=False,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


# Conexion para conversaciones activas (clave chat:conv:* / chat:idx:user:*)
redis_client = _build_client(REDIS_DB_CONVERSATIONS)

# Conexion para contexto conversacional (ventana, resumen, loop detection)
context_redis_client = _build_client(REDIS_DB_CONTEXT)

# MongoDB eliminado en esta rama. Se mantiene el simbolo para compatibilidad
# con codigo legado que lo importa con manejo defensivo.
mongo_db = None
