import json
import logging
from datetime import datetime, timedelta
import uuid

# MongoDB eliminado en esta rama (ai-microservices-disaster). Los imports de
# bson/pymongo se mantienen protegidos para no romper si la libreria no esta
# instalada; ya no se usan en el flujo (Redis es el unico backend de
# conversaciones activas).
try:  # pragma: no cover
    from bson import Binary
    from bson.binary import UuidRepresentation
    from pymongo import ASCENDING, DESCENDING
except Exception:  # pragma: no cover
    Binary = None
    UuidRepresentation = None
    ASCENDING = 1
    DESCENDING = -1

from data.connect import mongo_db, redis_client
from services.encryption import Encryption

# Configurar logger
logger = logging.getLogger(__name__)

LIFECYCLE_ACTIVE = "active"
LIFECYCLE_ARCHIVED = "archived"
LIFECYCLE_DELETED = "deleted"
LIFECYCLE_ALLOWED = {LIFECYCLE_ACTIVE, LIFECYCLE_ARCHIVED, LIFECYCLE_DELETED}
SOFT_DELETE_RETENTION_DAYS = 30
ENCRYPTED_CONVERSATION_SCHEMA_VERSION = 2


# --- Cifrado de campos sensibles para Redis ---------------------------------
# Mismo esquema que ConversationalDatasetManager usaba para Mongo: se cifran
# los campos `messages` y `medical_context` con Fernet antes de almacenar.

def _conv_encryption():
    return Encryption()


def _encrypt_conv_field(value):
    if value is None:
        return value
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    return _conv_encryption().encrypt_string(serialized)


def _decrypt_conv_field(value):
    if value in (None, ""):
        return value
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return value
    try:
        return json.loads(_conv_encryption().decrypt_string(value))
    except Exception:
        try:
            return json.loads(value)
        except Exception:
            return value

class ConversationalDatasetManager:
    
    def __init__(self):
        # MongoDB eliminado: el unico backend de conversaciones activas es Redis
        # (RedisCacheManager). Se mantiene `self.collection = None` para que el
        # codigo legado que lo consultaba con manejo defensivo no rompa.
        self.collection = None
        self._cache = RedisCacheManager
        logger.info("ConversationalDatasetManager inicializado sobre Redis (sin Mongo)")

    def _normalize_lifecycle_status(self, conversation):
        if not isinstance(conversation, dict):
            return LIFECYCLE_ACTIVE
        raw = str(conversation.get("lifecycle_status") or "").strip().lower()
        if raw in LIFECYCLE_ALLOWED:
            return raw
        if conversation.get("active") is False:
            return LIFECYCLE_ARCHIVED
        return LIFECYCLE_ACTIVE

    def _apply_lifecycle_backfill(self, conversation):
        if not isinstance(conversation, dict):
            return conversation
        lifecycle_status = self._normalize_lifecycle_status(conversation)
        conversation["lifecycle_status"] = lifecycle_status
        conversation["active"] = lifecycle_status == LIFECYCLE_ACTIVE
        conversation.setdefault("archived_at", None)
        conversation.setdefault("deleted_at", None)
        conversation.setdefault("purge_after", None)
        return conversation

    def _serialize_conversation_record(self, conversation):
        if not isinstance(conversation, dict):
            return conversation
        if "_id" in conversation and isinstance(conversation["_id"], Binary):
            conversation["_id"] = self._binary_to_uuid(conversation["_id"])
        conversation = self._decrypt_sensitive_fields(conversation)
        return self._apply_lifecycle_backfill(conversation)

    def _encryption(self):
        return Encryption()

    def _encrypt_json_field(self, value):
        if value is None:
            return value
        serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        return self._encryption().encrypt_string(serialized)

    def _decrypt_json_field(self, value):
        if value in (None, ""):
            return value
        if isinstance(value, (dict, list)):
            return value
        if not isinstance(value, str):
            return value

        try:
            decrypted = self._encryption().decrypt_string(value)
            return json.loads(decrypted)
        except Exception:
            try:
                return json.loads(value)
            except Exception:
                return value

    def _encrypt_sensitive_fields(self, conversation):
        if not isinstance(conversation, dict):
            return conversation
        encrypted = dict(conversation)
        encrypted["messages"] = self._encrypt_json_field(conversation.get("messages", []))
        encrypted["medical_context"] = self._encrypt_json_field(conversation.get("medical_context", {}))
        encrypted["schema_version"] = ENCRYPTED_CONVERSATION_SCHEMA_VERSION
        return encrypted

    def _decrypt_sensitive_fields(self, conversation):
        if not isinstance(conversation, dict):
            return conversation
        decrypted = dict(conversation)
        if "messages" in decrypted:
            decrypted["messages"] = self._decrypt_json_field(decrypted.get("messages"))
        if "medical_context" in decrypted:
            decrypted["medical_context"] = self._decrypt_json_field(decrypted.get("medical_context"))
        return decrypted

    def _uuid_to_binary(self, uuid_obj):
        """Convierte un UUID a Binary para MongoDB"""
        if isinstance(uuid_obj, str):
            uuid_obj = uuid.UUID(uuid_obj)
        return Binary.from_uuid(uuid_obj, UuidRepresentation.STANDARD)

    def _binary_to_uuid(self, binary_obj):
        """Convierte un Binary de MongoDB a UUID string"""
        if isinstance(binary_obj, Binary):
            return str(binary_obj.as_uuid())
        return str(binary_obj)

    def add_conversation(
        self,
        user_id,
        medical_context,
        messages,
        symptoms,
        symptoms_pattern,
        pain_scale,
        triaje_level,
        conversation_id=None,
    ):
        try:
            conversation_id = str(conversation_id or uuid.uuid4())
            RedisCacheManager.guardar_conversacion(
                user_id, conversation_id, medical_context, messages,
                symptoms, symptoms_pattern, pain_scale, triaje_level,
            )
            logger.info(f"Conversación {conversation_id} agregada a Redis para el usuario {user_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"Error al agregar conversación: {str(e)}")
            raise

    def get_conversations(self, user_id, view="active"):
        try:
            selected_view = str(view or "active").strip().lower()
            if selected_view not in {"active", "archived", "all"}:
                selected_view = "active"

            # Redis es el unico backend: se leen todas las conversaciones del
            # indice del usuario y se filtra por lifecycle_status en Python
            # (volumen bajo por usuario, TTL 24h).
            raw_conversations = RedisCacheManager.obtener_todas_conversaciones(user_id)
            result = []
            for conv in raw_conversations:
                conv = self._apply_lifecycle_backfill(conv)
                status = self._normalize_lifecycle_status(conv)
                if status == LIFECYCLE_DELETED:
                    continue
                if selected_view == "active" and status != LIFECYCLE_ACTIVE:
                    continue
                if selected_view == "archived" and status != LIFECYCLE_ARCHIVED:
                    continue
                result.append(conv)

            result.sort(key=lambda c: str(c.get("timestamp") or ""), reverse=True)
            logger.info(f"Recuperadas {len(result)} conversaciones de Redis para el usuario {user_id}")
            return result
        except Exception as e:
            logger.error(f"Error al obtener conversaciones para el usuario {user_id}: {str(e)}")
            raise

    def get_conversation(self, user_id, conversation_id, include_deleted=False):
        try:
            cached_conversation = RedisCacheManager.obtener_conversacion(user_id, conversation_id)
            if cached_conversation:
                cached_conversation = self._apply_lifecycle_backfill(cached_conversation)
                lifecycle_status = self._normalize_lifecycle_status(cached_conversation)
                if lifecycle_status == LIFECYCLE_DELETED and not include_deleted:
                    return None
                logger.info(f"Conversación {conversation_id} recuperada de Redis para el usuario {user_id}")
                return cached_conversation
            logger.info(f"Conversación {conversation_id} no encontrada para el usuario {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error al obtener conversación {conversation_id} para el usuario {user_id}: {str(e)}")
            raise

    def update_conversation(self, user_id, conversation_id, messages=None, symptoms=None,
                           symptoms_pattern=None, pain_scale=None, triaje_level=None, medical_context=None):
        try:
            update_data = {"timestamp": datetime.now().isoformat()}

            if messages is not None:
                update_data["messages"] = messages
            if symptoms is not None:
                update_data["symptoms"] = symptoms
            if symptoms_pattern is not None:
                update_data["symptoms_pattern"] = symptoms_pattern
            if pain_scale is not None:
                update_data["pain_scale"] = pain_scale
            if triaje_level is not None:
                update_data["triaje_level"] = triaje_level
            if medical_context is not None:
                update_data["medical_context"] = medical_context

            cached_conversation = RedisCacheManager.obtener_conversacion(user_id, conversation_id)
            if not cached_conversation:
                logger.info(f"Conversación {conversation_id} no encontrada en Redis para actualizar")
                return 0
            if self._normalize_lifecycle_status(cached_conversation) == LIFECYCLE_DELETED:
                return 0

            for key, value in update_data.items():
                cached_conversation[key] = value
            RedisCacheManager.actualizar_conversacion(user_id, conversation_id, cached_conversation)
            logger.info(f"Conversación {conversation_id} actualizada en Redis para el usuario {user_id}")
            return 1
        except Exception as e:
            logger.error(f"Error al actualizar conversación {conversation_id} para el usuario {user_id}: {str(e)}")
            raise

    def update_conversation_etl_state(self, user_id, conversation_id, etl_state):
        try:
            if not isinstance(etl_state, dict):
                etl_state = {}

            existing_etl_state = {}
            try:
                current_conversation = self.get_conversation(user_id, conversation_id)
                if isinstance(current_conversation, dict):
                    medical_context = current_conversation.get("medical_context", {})
                    if isinstance(medical_context, dict):
                        hybrid_state = medical_context.get("hybrid_state", {})
                        if isinstance(hybrid_state, dict):
                            etl_payload = hybrid_state.get("etl", {})
                            if isinstance(etl_payload, dict):
                                existing_etl_state = etl_payload
            except Exception as state_error:
                logger.warning(
                    "No se pudo recuperar estado ETL previo para conversación %s: %s",
                    conversation_id,
                    str(state_error),
                )

            merged_state = {**existing_etl_state, **etl_state}

            cached_conversation = RedisCacheManager.obtener_conversacion(user_id, conversation_id)
            if not cached_conversation:
                return 0
            medical_context_cached = cached_conversation.get("medical_context", {})
            if not isinstance(medical_context_cached, dict):
                medical_context_cached = {}
            hybrid_state_cached = medical_context_cached.get("hybrid_state", {})
            if not isinstance(hybrid_state_cached, dict):
                hybrid_state_cached = {}
            hybrid_state_cached["etl"] = merged_state
            medical_context_cached["hybrid_state"] = hybrid_state_cached
            cached_conversation["medical_context"] = medical_context_cached
            cached_conversation["timestamp"] = datetime.now().isoformat()
            RedisCacheManager.actualizar_conversacion(user_id, conversation_id, cached_conversation)
            logger.info(
                "Estado ETL actualizado en Redis para conversación %s usuario %s",
                conversation_id,
                user_id,
            )
            return 1
        except Exception as e:
            logger.error(
                "Error al actualizar estado ETL para conversación %s usuario %s: %s",
                conversation_id,
                user_id,
                str(e),
            )
            raise

    def _set_lifecycle(self, user_id, conversation_id, *, expected_statuses, changes):
        """Actualiza in-place el lifecycle de una conversación en Redis.

        Mantiene el registro en Redis (no lo elimina) para que las vistas
        archived/all y la recuperacion sigan funcionando, igual que hacia
        Mongo con lifecycle_status.
        """
        cached = RedisCacheManager.obtener_conversacion(user_id, conversation_id)
        if not cached:
            return 0
        current_status = self._normalize_lifecycle_status(cached)
        if expected_statuses is not None and current_status not in expected_statuses:
            return 0
        cached.update(changes)
        cached["timestamp"] = datetime.now().isoformat()
        RedisCacheManager.actualizar_conversacion(user_id, conversation_id, cached)
        return 1

    def archive_conversation(self, user_id, conversation_id):
        try:
            now = datetime.now().isoformat()
            return self._set_lifecycle(
                user_id,
                conversation_id,
                expected_statuses={LIFECYCLE_ACTIVE},
                changes={
                    "lifecycle_status": LIFECYCLE_ARCHIVED,
                    "archived_at": now,
                    "deleted_at": None,
                    "purge_after": None,
                    "active": False,
                },
            )
        except Exception as e:
            logger.error(f"Error al archivar conversación {conversation_id} para el usuario {user_id}: {str(e)}")
            raise

    def recover_conversation(self, user_id, conversation_id):
        try:
            return self._set_lifecycle(
                user_id,
                conversation_id,
                expected_statuses={LIFECYCLE_ARCHIVED},
                changes={
                    "lifecycle_status": LIFECYCLE_ACTIVE,
                    "archived_at": None,
                    "deleted_at": None,
                    "purge_after": None,
                    "active": True,
                },
            )
        except Exception as e:
            logger.error(f"Error al recuperar conversación {conversation_id} para el usuario {user_id}: {str(e)}")
            raise

    def soft_delete_conversation(self, user_id, conversation_id):
        try:
            now = datetime.now()
            purge_after = now + timedelta(days=SOFT_DELETE_RETENTION_DAYS)
            return self._set_lifecycle(
                user_id,
                conversation_id,
                expected_statuses={LIFECYCLE_ACTIVE, LIFECYCLE_ARCHIVED},
                changes={
                    "lifecycle_status": LIFECYCLE_DELETED,
                    "deleted_at": now.isoformat(),
                    "purge_after": purge_after.isoformat(),
                    "active": False,
                },
            )
        except Exception as e:
            logger.error(f"Error al hacer soft-delete de conversación {conversation_id} para el usuario {user_id}: {str(e)}")
            raise

    def soft_delete_all_conversations(self, user_id):
        try:
            raw_conversations = RedisCacheManager.obtener_todas_conversaciones(user_id)
            count = 0
            for conv in raw_conversations:
                conv_id = conv.get("_id")
                if not conv_id:
                    continue
                count += self.soft_delete_conversation(user_id, conv_id)
            return count
        except Exception as e:
            logger.error(f"Error al hacer soft-delete masivo para el usuario {user_id}: {str(e)}")
            raise

    def mark_conversation_inactive(self, user_id, conversation_id):
        return self.archive_conversation(user_id, conversation_id)

    def delete_conversation(self, user_id, conversation_id):
        return self.soft_delete_conversation(user_id, conversation_id)

    def delete_all_conversations(self, user_id):
        return self.soft_delete_all_conversations(user_id)

class RedisCacheManager:
    # Constantes
    EXPIRATION_TIME = 60 * 60 * 24  # 24 horas en segundos
    
    @staticmethod
    def _get_key(user_id, conversation_id=None):
        """Genera la clave para Redis"""
        try:
            if conversation_id:
                return f"chat:conv:{user_id}:{conversation_id}"
            return f"chat:idx:user:{user_id}"
        except Exception as e:
            logger.error(f"Error al generar clave Redis: {str(e)}")
            raise

    @staticmethod
    def _encrypt_payload(data):
        """Cifra los campos sensibles (messages, medical_context) antes de
        persistir en Redis. El resto de campos se mantienen en claro para
        permitir filtrado por lifecycle_status sin descifrar."""
        if not isinstance(data, dict):
            return data
        encrypted = dict(data)
        if "messages" in encrypted:
            encrypted["messages"] = _encrypt_conv_field(encrypted.get("messages"))
        if "medical_context" in encrypted:
            encrypted["medical_context"] = _encrypt_conv_field(encrypted.get("medical_context"))
        encrypted["schema_version"] = ENCRYPTED_CONVERSATION_SCHEMA_VERSION
        return encrypted

    @staticmethod
    def _decrypt_payload(data):
        """Descifra los campos sensibles al leer de Redis. Tolera registros
        antiguos en texto plano (fallback en _decrypt_conv_field)."""
        if not isinstance(data, dict):
            return data
        decrypted = dict(data)
        if "messages" in decrypted:
            decrypted["messages"] = _decrypt_conv_field(decrypted.get("messages"))
        if "medical_context" in decrypted:
            decrypted["medical_context"] = _decrypt_conv_field(decrypted.get("medical_context"))
        return decrypted

    @staticmethod
    def guardar_conversacion(user_id, conversation_id, medical_context, messages, symptoms,
                           symptoms_pattern, pain_scale, triaje_level,
                           lifecycle_status=LIFECYCLE_ACTIVE, archived_at=None, deleted_at=None, purge_after=None):
        """Guarda una conversación en Redis con expiración de 24 horas"""
        try:
            normalized_status = lifecycle_status if lifecycle_status in LIFECYCLE_ALLOWED else LIFECYCLE_ACTIVE
            data = {
                "user_id": user_id,
                "_id": conversation_id,  # Mantener como string en Redis
                "symptoms": symptoms,
                "symptoms_pattern": symptoms_pattern,
                "pain_scale": pain_scale,
                "triaje_level": triaje_level,
                "medical_context": medical_context,
                "messages": messages,
                "timestamp": datetime.now().isoformat(),
                "active": normalized_status == LIFECYCLE_ACTIVE,
                "lifecycle_status": normalized_status,
                "archived_at": archived_at.isoformat() if isinstance(archived_at, datetime) else archived_at,
                "deleted_at": deleted_at.isoformat() if isinstance(deleted_at, datetime) else deleted_at,
                "purge_after": purge_after.isoformat() if isinstance(purge_after, datetime) else purge_after,
            }

            # Guardar la conversación con expiración (campos sensibles cifrados)
            key = RedisCacheManager._get_key(user_id, conversation_id)
            redis_client.set(key, json.dumps(RedisCacheManager._encrypt_payload(data)), ex=RedisCacheManager.EXPIRATION_TIME)
            logger.debug(f"Datos guardados en Redis con clave: {key}")
            
            # Añadir a la lista de conversaciones del usuario
            user_key = RedisCacheManager._get_key(user_id)
            redis_client.sadd(user_key, conversation_id)
            redis_client.expire(user_key, RedisCacheManager.EXPIRATION_TIME)
            logger.debug(f"Conversación {conversation_id} añadida al conjunto de usuario: {user_key}")
            
            return data
        except Exception as e:
            logger.error(f"Error al guardar conversación en Redis para usuario {user_id}, conversación {conversation_id}: {str(e)}")
            raise

    @staticmethod
    def obtener_conversacion(user_id, conversation_id):
        """Obtiene una conversación específica de Redis"""
        try:
            key = RedisCacheManager._get_key(user_id, conversation_id)
            data = redis_client.get(key)
            
            # Renovar el tiempo de expiración cuando se accede
            if data:
                redis_client.expire(key, RedisCacheManager.EXPIRATION_TIME)
                logger.debug(f"Tiempo de expiración renovado para clave: {key}")
                return RedisCacheManager._decrypt_payload(json.loads(data))
            logger.debug(f"No se encontró datos en Redis para clave: {key}")
            return None
        except json.JSONDecodeError as je:
            logger.error(f"Error al decodificar JSON desde Redis para usuario {user_id}, conversación {conversation_id}: {str(je)}")
            return None
        except Exception as e:
            logger.error(f"Error al obtener conversación de Redis para usuario {user_id}, conversación {conversation_id}: {str(e)}")
            raise
    
    @staticmethod
    def actualizar_conversacion(user_id, conversation_id, data):
        """Actualiza una conversación en Redis"""
        try:
            # Asegurar que timestamp sea serializable
            if 'timestamp' in data and isinstance(data['timestamp'], datetime):
                data['timestamp'] = data['timestamp'].isoformat()
            
            key = RedisCacheManager._get_key(user_id, conversation_id)
            redis_client.set(key, json.dumps(RedisCacheManager._encrypt_payload(data)), ex=RedisCacheManager.EXPIRATION_TIME)
            logger.debug(f"Conversación actualizada en Redis con clave: {key}")
            return True
        except Exception as e:
            logger.error(f"Error al actualizar conversación en Redis para usuario {user_id}, conversación {conversation_id}: {str(e)}")
            raise
    
    @staticmethod
    def eliminar_conversacion(user_id, conversation_id):
        """Elimina una conversación específica de Redis"""
        try:
            # Eliminar la conversación
            key = RedisCacheManager._get_key(user_id, conversation_id)
            redis_client.delete(key)
            logger.debug(f"Eliminada conversación de Redis con clave: {key}")
            
            # Eliminar de la lista de conversaciones del usuario
            user_key = RedisCacheManager._get_key(user_id)
            redis_client.srem(user_key, conversation_id)
            logger.debug(f"Conversación {conversation_id} eliminada del conjunto de usuario: {user_key}")
            
            return True
        except Exception as e:
            logger.error(f"Error al eliminar conversación de Redis para usuario {user_id}, conversación {conversation_id}: {str(e)}")
            raise
    
    @staticmethod
    def eliminar_todas_conversaciones(user_id):
        """Elimina todas las conversaciones de un usuario en Redis"""
        try:
            # Obtener todas las IDs de conversación para este usuario
            user_key = RedisCacheManager._get_key(user_id)
            conversation_ids = redis_client.smembers(user_key)
            
            # Eliminar cada conversación
            for conv_id in conversation_ids:
                try:
                    key = RedisCacheManager._get_key(user_id, conv_id.decode('utf-8'))
                    redis_client.delete(key)
                    logger.debug(f"Eliminada conversación de Redis con clave: {key}")
                except Exception as inner_e:
                    logger.warning(f"Error al eliminar conversación individual {conv_id}: {str(inner_e)}")
            
            # Eliminar la lista de conversaciones
            redis_client.delete(user_key)
            logger.debug(f"Eliminado conjunto de usuario: {user_key}")
            
            return True
        except Exception as e:
            logger.error(f"Error al eliminar todas las conversaciones de Redis para usuario {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def obtener_todas_conversaciones(user_id):
        """Obtiene todas las conversaciones de un usuario en Redis"""
        try:
            # Obtener todas las IDs de conversación para este usuario
            user_key = RedisCacheManager._get_key(user_id)
            conversation_ids = redis_client.smembers(user_key)
            
            conversations = []
            for conv_id in conversation_ids:
                try:
                    conv_id = conv_id.decode('utf-8')
                    data = RedisCacheManager.obtener_conversacion(user_id, conv_id)
                    if data:
                        conversations.append(data)
                except Exception as inner_e:
                    logger.warning(f"Error al obtener conversación individual {conv_id}: {str(inner_e)}")
            
            logger.debug(f"Recuperadas {len(conversations)} conversaciones de Redis para usuario {user_id}")
            return conversations
        except Exception as e:
            logger.error(f"Error al obtener todas las conversaciones de Redis para usuario {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def verificar_expiracion(user_id, conversation_id):
        """Verifica el tiempo restante de expiración para una conversación"""
        try:
            key = RedisCacheManager._get_key(user_id, conversation_id)
            ttl = redis_client.ttl(key)
            if ttl > 0:
                logger.info(f"Tiempo restante para expiración de conversación {conversation_id}: {ttl} segundos")
                return ttl
            else:
                logger.info(f"La conversación {conversation_id} no existe o no tiene tiempo de expiración configurado")
                return None
        except Exception as e:
            logger.error(f"Error al verificar expiración para usuario {user_id}, conversación {conversation_id}: {str(e)}")
            raise
    
    @staticmethod
    def extender_expiracion(user_id, conversation_id, horas=24):
        """Extiende el tiempo de expiración de una conversación"""
        try:
            key = RedisCacheManager._get_key(user_id, conversation_id)
            segundos = int(horas * 60 * 60)
            result = redis_client.expire(key, segundos)
            
            if result:
                logger.info(f"Expiración extendida a {horas} horas para conversación {conversation_id}")
                
                # También extender el conjunto de usuario
                user_key = RedisCacheManager._get_key(user_id)
                redis_client.expire(user_key, segundos)
                
                return True
            else:
                logger.warning(f"No se pudo extender expiración para conversación {conversation_id}, posiblemente no existe")
                return False
        except Exception as e:
            logger.error(f"Error al extender expiración para usuario {user_id}, conversación {conversation_id}: {str(e)}")
            raise
