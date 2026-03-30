from config.config import Config
from pymongo import MongoClient
from bson.codec_options import CodecOptions
from bson.binary import UuidRepresentation
import redis
import ssl

# Configurar el cliente MongoDB con UUID representation
MONGO_URI = f"mongodb://{Config.MONGO_USER}:{Config.MONGO_PASS}@{Config.MONGO_HOST}:{Config.MONGO_PORT}/{Config.MONGO_DB}?authSource=admin"

# Crear cliente con configuración de UUID
mongo_client = MongoClient(MONGO_URI, uuidRepresentation='standard')

# Configurar la base de datos con opciones de codec
codec_options = CodecOptions(uuid_representation=UuidRepresentation.STANDARD)
mongo_db = mongo_client[Config.MONGO_DB].with_options(codec_options=codec_options)


def _redis_ssl_cert_reqs():
    mapping = {
        "none": ssl.CERT_NONE,
        "optional": ssl.CERT_OPTIONAL,
        "required": ssl.CERT_REQUIRED,
    }
    return mapping.get(Config.REDIS_SSL_CERT_REQS, ssl.CERT_REQUIRED)


def _redis_kwargs(db: int):
    kwargs = {
        "host": Config.REDIS_HOST,
        "port": Config.REDIS_PORT,
        "db": db,
        "password": Config.REDIS_PASSWORD,
        "decode_responses": True,
    }
    if Config.REDIS_USE_TLS:
        kwargs["ssl"] = True
        kwargs["ssl_cert_reqs"] = _redis_ssl_cert_reqs()
    return kwargs


redis_client = redis.Redis(**_redis_kwargs(Config.REDIS_DB))
context_redis_client = redis.Redis(**_redis_kwargs(Config.CHAT_REDIS_DB_CONTEXT))

# Verificar conexiones
try:
    mongo_client.server_info()  # Prueba la conexión a MongoDB
    print("✅ Conexión exitosa a MongoDB")
except Exception as e:
    print(f"❌ Error conectando a MongoDB: {e}")

try:
    redis_client.ping()  # Prueba la conexión a Redis
    print("✅ Conexión exitosa a Redis")
except Exception as e:
    print(f"❌ Error conectando a Redis: {e}")

try:
    context_redis_client.ping()  # Prueba la conexión a Redis para contexto
    print("✅ Conexión exitosa a Redis (contexto)")
except Exception as e:
    print(f"❌ Error conectando a Redis de contexto: {e}")
