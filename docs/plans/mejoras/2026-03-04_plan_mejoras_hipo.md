# Plan de Mejoras Técnicas — Chatbot de Triaje Médico Hipo

**TFG · Arquitectura Flask + Django + Worker Celery + RabbitMQ ETL**  
**38 mejoras · 8 bloques · Listo para agente IA**

---

## Índice rápido

| # | Mejora | Servicio | Prioridad |
|---|--------|----------|-----------|
| 1 | Firma HMAC-SHA256 en peticiones Flask → Django | Ambos | 🔴 CRÍTICO |
| 2 | Tabla AuditLog con firma criptográfica | Django | 🔴 CRÍTICO |
| 3 | Cifrado de campos clínicos en PostgreSQL | Django | 🔴 CRÍTICO |
| 4 | Cifrado de mensajes clínicos en MongoDB | Flask | 🔴 CRÍTICO |
| 5 | Autenticación y TLS en Redis | Ambos | 🔴 CRÍTICO |
| 6 | Tokens de acceso firmados para endpoints sensibles | Django | 🟡 IMPORTANTE |
| 7 | Corrección de la clase Encryption de Flask | Flask | 🟡 IMPORTANTE |
| 8 | Eliminar CORS wildcard en métodos options() manuales | Django | 🟡 IMPORTANTE |
| 9 | Rate limiting en WebSocket por usuario | Flask | 🔴 CRÍTICO |
| 10 | Mover AUTHENTICATED_USERS_BY_SID a Redis | Flask | 🔴 CRÍTICO |
| 11 | Validación de variables de entorno críticas al arranque | Flask | 🟡 IMPORTANTE |
| 12 | Health check endpoints en Flask y Django | Ambos | 🟡 IMPORTANTE |
| 13 | Throttling en endpoints de autenticación Django | Django | 🟡 IMPORTANTE |
| 14 | Rectificación de detect_finalization — ETL prematura | Flask | 🟡 IMPORTANTE |
| 15 | Corrección N+1 queries en PatientSerializer | Django | 🟡 IMPORTANTE |
| 16 | Reducir ACCESS_TOKEN_LIFETIME de JWT a 15 minutos | Django | 🟡 IMPORTANTE |
| 17 | Worker Celery (chat) + Worker ETL con RabbitMQ | Nuevo | 🟢 NUEVO |
| 18 | Flask como gateway WebSocket ligero | Flask | 🟢 NUEVO |
| 19 | Endpoint de reintento manual de ETL vía RabbitMQ | Flask | 🟢 NUEVO |
| 20 | Caché Redis de resultados ETL | ETL Worker | 🟢 NUEVO |
| 21 | Reorganización DBs Redis por función | Ambos | ⚪ MEJORA |
| 22 | Content-Security-Policy en Nginx | Nginx | 🟡 IMPORTANTE |
| 23 | Ampliar casos clínicos del sistema experto | Flask | 🟡 IMPORTANTE |
| 24 | Token WebSocket en primer mensaje en lugar de query param | Flask | 🟡 IMPORTANTE |
| 25 | Evento triage_escalation en WebSocket | Flask | ⚪ MEJORA |
| 26 | Respuesta de origen visible para el usuario (response_source) | Flask | ⚪ MEJORA |
| 27 | Optimizar prompt INITIAL_PROMPT — reducir tokens | Flask | ⚪ MEJORA |
| 28 | Mocks de AWS en tests unitarios | Flask | ⚪ MEJORA |
| 29 | Memoria longitudinal entre conversaciones | Flask | 🔴 CRÍTICO |
| 30 | Detección de contradicciones intra-conversación | Flask | 🔴 CRÍTICO |
| 31 | Pregunta de cierre post-triaje | Flask | 🟡 IMPORTANTE |
| 32 | Red flags con contexto temporal e intensidad | Flask | 🟡 IMPORTANTE |
| 33 | Modo "segunda opinión" para médico | Django + Flask | 🟢 NUEVO |
| 34 | Confianza visible en el consejo final | Flask | ⚪ MEJORA |
| 35 | Aviso visible de timeout por inactividad | Flask + WS + Frontend | 🔴 CRÍTICO |
| 36 | Detección de idioma + respuesta multilingüe | Flask | ⚪ MEJORA |
| 37 | Resumen visible al finalizar | Flask + Worker + WS | ⚪ MEJORA |
| 38 | Caché de sistema experto para casos idénticos | Flask + Redis | ⚪ MEJORA |

---

## Orden de ejecución recomendado

1. **🔴 CRÍTICO** (#1–#10, #29, #30, #35) — Bloqueantes para seguridad, estabilidad y calidad clínica básica
2. **🟡 IMPORTANTE** (#11–#16, #22–#24, #31, #32) — Robustez sin nueva arquitectura
3. **🟢 NUEVO** (#17–#20, #33) — Requiere crear el Worker antes que #18, #19, #20
4. **⚪ MEJORA** (#21, #25–#28, #34, #36–#38) — Optimizaciones incrementales independientes

### Dependencias críticas entre mejoras

- `#2` (AuditLog) → antes de `#3`, `#4` (cualquier modificación de datos clínicos)
- `#4` (cifrado MongoDB) → antes de `#20` (caché ETL Redis)
- `#10` (Redis auth WS) → antes de `#24` (token en primer mensaje)
- `#16` (reducir token lifetime) → requiere cambios en frontend para renovación automática
- `#17` (Worker Celery + ETL Worker RabbitMQ) → antes de `#18`, `#19`, `#20`
- `#21` (reorganización Redis) → antes de `#38` (caché sistema experto)
- `#35` (timeout WS) → coordinado con `#31` (cierre post-triaje)

---

## Prompt de entrada para el agente

```
Implementa la mejora #N del plan de mejoras del chatbot Hipo.

El repositorio está en [ruta]. Los archivos a modificar son los indicados
en la tarjeta de la mejora. Sigue exactamente los pasos de implementación
en el orden indicado. Al terminar, ejecuta los tests existentes para
verificar que no hay regresiones.
```

---

## Bloque 1 — Seguridad: Firma y cifrado

### #1 — Firma HMAC-SHA256 en peticiones Flask → Django

**Servicio:** Ambos | **Prioridad:** 🔴 CRÍTICO

**Problema:** Las peticiones internas de Flask a Django no están firmadas. Un atacante que acceda a la red Docker puede inyectar o modificar datos clínicos sin que Django lo detecte. HMAC-SHA256 con timestamp previene replay attacks y garantiza integridad en tránsito.

**Archivos afectados:**
- `flask-services/src/services/api/send_api.py`
- `django_services/users/views.py` → `PatientMedicalDataUpdateView`

**Pasos:**
1. En `send_api.py`: generar `timestamp` + firma `HMAC-SHA256(SECRET_KEY, timestamp:json_canonico)`
2. Añadir cabeceras `X-Request-Timestamp` y `X-Request-Signature` a cada petición interna
3. En `PatientMedicalDataUpdateView`: verificar firma y rechazar si `timestamp > 30 segundos`
4. Usar `hmac.compare_digest()` para la comparación (previene timing attacks)
5. Crear `FLASK_API_KEY` separada del `SECRET_KEY` de Django en variables de entorno

---

### #2 — Tabla AuditLog con firma criptográfica

**Servicio:** Django | **Prioridad:** 🔴 CRÍTICO

**Problema:** No existe registro inmutable de quién modificó datos clínicos ni cuándo. El RGPD y el AI Act exigen trazabilidad completa para sistemas de IA de alto riesgo.

**Archivos afectados:**
- `django_services/users/models.py` → nuevo modelo `AuditLog`
- `django_services/users/utils/audit.py` → nuevo fichero
- `django_services/users/views.py` → llamadas a `create_audit_entry()`

**Pasos:**
1. Crear modelo `AuditLog` con campos: `actor_user`, `actor_service`, `actor_ip`, `action`, `resource_type`, `resource_id`, `data_before` (JSON), `data_after` (JSON), `content_hash`, `signature`, `timestamp`
2. Crear `AUDIT_SIGNING_KEY` en `.env` — clave independiente del `SECRET_KEY`
3. Implementar `create_audit_entry()`: serializa contenido, calcula SHA-256, firma con HMAC
4. Implementar `verify_audit_entry()`: recalcula hash y firma, compara con stored
5. Llamar a `create_audit_entry()` en: `PatientMedicalDataUpdateView`, `PatientHistoryCreateView`, `AccountDeleteView`
6. Crear migración Django para la nueva tabla

---

### #3 — Cifrado de campos clínicos en PostgreSQL

**Servicio:** Django | **Prioridad:** 🔴 CRÍTICO

**Problema:** `medical_context`, `allergies`, `medications` y `medical_history` se guardan en texto claro en PostgreSQL. Acceso directo a la base de datos expone datos sanitarios sensibles.

**Archivos afectados:**
- `django_services/users/models.py` → `Patient` y `PatientHistoryEntry`
- `django_services/config/settings.py` → `FIELD_ENCRYPTION_KEY`
- `django_services/requirements.txt`

**Pasos:**
1. Instalar: `pip install django-encrypted-model-fields`
2. Añadir `FIELD_ENCRYPTION_KEY` en `.env` con clave de 32 bytes generada con `Fernet.generate_key()`
3. En `models.py`: cambiar `TextField` a `EncryptedTextField` en `medical_context`, `allergies`, `medications`, `medical_history`
4. Crear y aplicar migración Django — los datos existentes requieren script de migración para cifrar
5. Verificar que los campos cifrados no se usan en filtros SQL (incompatible con cifrado en reposo)

---

### #4 — Cifrado de mensajes clínicos en MongoDB

**Servicio:** Flask | **Prioridad:** 🔴 CRÍTICO

**Problema:** Los mensajes de conversación y `medical_context` se almacenan en texto claro en MongoDB. Fernet con clave derivada del `SECRET_KEY` cifra el contenido antes de persistir.

**Archivos afectados:**
- `flask-services/src/models/conversation.py` → `add_conversation()`, `get_conversation()`
- `flask-services/src/data/connect.py`
- `flask-services/src/config/config.py`

**Pasos:**
1. En `config.py`: añadir `MONGO_ENCRYPTION_KEY` derivada con `hashlib.sha256(SECRET_KEY).digest()` → base64
2. En `conversation.py`: crear `_get_fernet()` que devuelva instancia Fernet con esa clave
3. En `add_conversation()`: cifrar campos `messages` y `medical_context` antes de `insert_one()`
4. En `get_conversation()` y `get_conversations()`: descifrar al leer si el campo es string cifrado
5. Añadir campo `schema_version` al documento para manejar migración de datos existentes

---

### #5 — Autenticación y TLS en Redis

**Servicio:** Ambos | **Prioridad:** 🔴 CRÍTICO

**Problema:** Los clientes Redis se crean sin contraseña ni TLS. Redis almacena contexto conversacional, JWT blacklist y tokens de sesión. Acceso sin autenticación expone toda esa información.

**Archivos afectados:**
- `flask-services/src/data/connect.py`
- `django_services/config/settings.py` → `CACHES`
- `docker-compose.yml` → servicio redis

**Pasos:**
1. Añadir `REDIS_PASSWORD` en `.env` y en el servicio redis del docker-compose con `requirepass`
2. Actualizar `redis.Redis()` en `connect.py` con parámetro `password=Config.REDIS_PASSWORD`
3. Actualizar `CACHES` en `settings.py` de Django con `LOCATION` que incluya `:password@`
4. En producción real añadir `ssl=True` y `ssl_cert_reqs='required'` a los clientes Redis

---

### #6 — Tokens de acceso firmados para endpoints sensibles

**Servicio:** Django | **Prioridad:** 🟡 IMPORTANTE

**Problema:** Los endpoints sensibles exponen UUID directamente en la URL (`/patients/uuid/history/`). El UUID es predecible y reutilizable indefinidamente.

**Archivos afectados:**
- `django_services/users/views.py` → `PatientMeHistoryView`, `PatientHistoryViewSet`
- `django_services/users/urls.py`

**Pasos:**
1. Crear endpoint `GET /patients/me/history/token/` que devuelva `django.core.signing.dumps({patient_id, action: 'read_history'}, max_age=300)`
2. Modificar el endpoint de historial para aceptar `?token=` y verificar con `signing.loads()`
3. El frontend solicita primero el token, luego lo usa para acceder al recurso — válido 5 minutos
4. Aplicar mismo patrón a cualquier endpoint que exponga IDs de recursos médicos en URL

---

### #7 — Corrección de la clase Encryption de Flask

**Servicio:** Flask | **Prioridad:** 🟡 IMPORTANTE

**Problema:** La clase `Encryption` en `encryption.py` deriva la clave Fernet de los primeros 32 bytes del payload JWT en texto plano. Eso no es entropía criptográfica válida y la clave es predecible. Además la clase nunca se usa en el flujo real.

**Archivos afectados:**
- `flask-services/src/services/security/encryption.py`

**Pasos:**
1. Reemplazar la derivación de clave: usar `hashlib.sha256(Config.SECRET_KEY.encode()).digest()` → `base64.urlsafe_b64encode()`
2. Eliminar la rama `if jwt_token` — la clave debe ser fija del servidor, no del usuario
3. Integrar la clase en el cifrado de MongoDB (mejora #4) para que realmente se use

---

### #8 — Eliminar CORS wildcard en métodos options() manuales

**Servicio:** Django | **Prioridad:** 🟡 IMPORTANTE

**Problema:** `LoginView`, `RegisterUserView` y `GoogleOAuthLoginView` tienen métodos `options()` con `Access-Control-Allow-Origin: '*'` hardcodeado, que sobreescriben la configuración segura de `django-cors-headers` en producción.

**Archivos afectados:**
- `django_services/users/views.py` → `LoginView`, `RegisterUserView`, `GoogleOAuthLoginView`

**Pasos:**
1. Eliminar completamente los métodos `options()` de las tres vistas
2. `django-cors-headers` gestiona los preflight automáticamente con la configuración del `settings.py`
3. Verificar que `CORS_ALLOWED_ORIGINS` en `settings.py` tiene solo los orígenes del frontend

---

## Bloque 2 — Estabilidad del servidor

### #9 — Rate limiting en WebSocket por usuario

**Servicio:** Flask | **Prioridad:** 🔴 CRÍTICO

**Problema:** No existe ningún límite de mensajes por usuario en el canal WebSocket. Un bug del frontend o un usuario malicioso puede generar miles de mensajes por segundo, creando llamadas ilimitadas a Bedrock (coste descontrolado) y saturando Flask.

**Archivos afectados:**
- `flask-services/src/routes/sockets_events.py` → `handle_chat_message()`
- `flask-services/src/data/connect.py`

**Pasos:**
1. Al inicio de `handle_chat_message()`: `rate_key = f'rate:{sid}'`, incrementar con redis `INCR`
2. Si `count == 1`: añadir `EXPIRE` de 60 segundos (ventana deslizante de 1 minuto)
3. Si `count > 20`: emitir error `'Demasiados mensajes, espera un momento'` y hacer `return`
4. Ajustar el límite (20/min) según el caso de uso real del chatbot médico

---

### #10 — Mover AUTHENTICATED_USERS_BY_SID a Redis

**Servicio:** Flask | **Prioridad:** 🔴 CRÍTICO

**Problema:** El diccionario `AUTHENTICATED_USERS_BY_SID` vive en memoria del proceso Flask. Si Flask se reinicia o hay múltiples workers/instancias, el estado se pierde o no se comparte. Autenticación WebSocket se rompe silenciosamente.

**Archivos afectados:**
- `flask-services/src/routes/sockets_events.py`
- `flask-services/src/data/connect.py`

**Pasos:**
1. Reemplazar `AUTHENTICATED_USERS_BY_SID` dict por operaciones Redis
2. En `handle_connect()`: `context_redis_client.setex(f'ws:auth:{sid}', 3600, user_id)`
3. En `resolve_ws_user_id()`: leer `context_redis_client.get(f'ws:auth:{sid}')`
4. En `handle_disconnect()`: `context_redis_client.delete(f'ws:auth:{sid}')`
5. Mismo patrón para `ACTIVE_CONVERSATION_BY_SID`

---

### #11 — Validación de variables de entorno críticas al arranque

**Servicio:** Flask | **Prioridad:** 🟡 IMPORTANTE

**Problema:** Si `AWS_REGION`, `SECRET_KEY` o `JWT_ALGORITHM` no están definidas en `.env`, Flask arranca con `None` silenciosamente y falla en el primer mensaje con un traceback críptico.

**Archivos afectados:**
- `flask-services/src/config/config.py`
- `flask-services/src/app.py`

**Pasos:**
1. Añadir método `classmethod Config.validate()` que compruebe las variables críticas
2. Variables requeridas: `SECRET_KEY`, `JWT_ALGORITHM`, `AWS_REGION`, `MONGO_HOST`, `REDIS_HOST`
3. Si alguna es `None` o vacía: lanzar `EnvironmentError` con lista de variables faltantes
4. Llamar `Config.validate()` en `create_app()` antes de `init_app()`

---

### #12 — Health check endpoints en Flask y Django

**Servicio:** Ambos | **Prioridad:** 🟡 IMPORTANTE

**Problema:** Ningún servicio expone un endpoint `/health`. Docker Compose no puede verificar si los servicios están realmente listos.

**Archivos afectados:**
- `flask-services/src/routes/chat_routes.py`
- `django_services/config/urls.py`
- `docker-compose.yml`

**Pasos:**
1. Flask: añadir `@app.route('/health')` que devuelva `{status: ok, mongo: ping, redis: ping}`
2. Django: añadir `path('health/', ...)` en `urls.py` que verifique DB y Redis
3. `docker-compose.yml` Flask: `healthcheck test: curl -f http://localhost:5000/health`
4. `docker-compose.yml` Django: `healthcheck test: curl -f http://localhost:8000/health`

---

### #13 — Throttling en endpoints de autenticación Django

**Servicio:** Django | **Prioridad:** 🟡 IMPORTANTE

**Problema:** `LoginView` y `PasswordResetRequestView` son `AllowAny` sin límite de intentos. Vulnerable a fuerza bruta de credenciales y flooding de emails de recuperación de contraseña.

**Archivos afectados:**
- `django_services/config/settings.py` → `REST_FRAMEWORK`

**Pasos:**
1. Añadir `DEFAULT_THROTTLE_CLASSES` en `REST_FRAMEWORK` con `AnonRateThrottle` y `UserRateThrottle`
2. Configurar `DEFAULT_THROTTLE_RATES`: `anon: '10/min'`, `user: '100/min'`
3. Para `LoginView` y `PasswordResetRequestView` crear throttle específico más restrictivo: `'5/min'`
4. Añadir clase `CustomLoginThrottle` que herede de `AnonRateThrottle` con `rate = '5/min'`

---

### #14 — Rectificación de detect_finalization — ETL prematura

**Servicio:** Flask | **Prioridad:** 🟡 IMPORTANTE

**Problema:** La ETL se dispara en el mismo turno en que el sistema experto genera el consejo final (`triage_recommendation`), antes de que el usuario lo haya leído. Si el usuario responde con una duda, ese turno puede no persistir correctamente en PostgreSQL.

**Archivos afectados:**
- `flask-services/src/services/chatbot/application/finalization_service.py`

**Pasos:**
1. Eliminar `'triage_recommendation'` como razón directa de disparo de ETL inmediata
2. Usar timer de inactividad (ya implementado) como mecanismo principal post-consejo
3. Solo disparar ETL inmediata en: emergencia confirmada, `explicit_close_phrase`, `websocket_disconnect`
4. Añadir flag `etl_pending` en `hybrid_state` para que el siguiente turno post-consejo registre correctamente

---

### #15 — Corrección N+1 queries en PatientSerializer

**Servicio:** Django | **Prioridad:** 🟡 IMPORTANTE

**Problema:** `PatientSerializer` incluye `DoctorBasicSerializer` anidado sin `prefetch_related`. Al listar pacientes, Django genera una query SQL por cada doctor de cada paciente. Con 100 pacientes y 3 doctores cada uno: 300 queries innecesarias.

**Archivos afectados:**
- `django_services/users/views.py` → `PatientViewSet.get_queryset()`

**Pasos:**
1. En `PatientViewSet.get_queryset()`: añadir `.prefetch_related('doctor_relations__doctor__user')`
2. En `DoctorViewSet.get_queryset()`: añadir `.select_related('user')` y `.prefetch_related('patient_relations__patient__user')`
3. En `PatientHistoryViewSet.get_queryset()`: añadir `.select_related('created_by', 'patient__user')`

---

### #16 — Reducir ACCESS_TOKEN_LIFETIME de JWT a 15 minutos

**Servicio:** Django | **Prioridad:** 🟡 IMPORTANTE

**Problema:** El access token dura 1 día. Cuando un usuario hace logout, Django invalida el refresh token pero el access token sigue válido 24 horas para el WebSocket de Flask. Ventana de ataque de 24 horas con token robado.

**Archivos afectados:**
- `django_services/config/settings.py` → `SIMPLE_JWT`

**Pasos:**
1. Cambiar `ACCESS_TOKEN_LIFETIME` de `timedelta(days=1)` a `timedelta(minutes=15)`
2. El frontend debe implementar renovación automática con el refresh token antes de expiración
3. En el WebSocket de Flask: manejar el error `401` por token expirado y solicitar renovación al frontend
4. `REFRESH_TOKEN_LIFETIME` puede mantenerse en 7 días

---

## Bloque 3 — Microservicio Worker Celery

### #17 — Worker Celery (chat) + Worker ETL con RabbitMQ

**Servicio:** Nuevo | **Prioridad:** 🟢 NUEVO

**Problema:** Flask actualmente bloquea un hilo por cada llamada a Bedrock (1–3 segundos). Con múltiples usuarios concurrentes los hilos se agotan. Además, la ETL escribe datos clínicos críticos en PostgreSQL: si se pierde una tarea, el dato médico desaparece para siempre.

La solución separa los dos casos de uso porque tienen requisitos opuestos:

| Tarea | Broker | Razón |
|-------|--------|-------|
| Mensajes chat → Bedrock | Redis DB3 + Celery | Latencia mínima; pérdida tolerable |
| ETL → Django/PostgreSQL | RabbitMQ | Garantía de entrega; dato clínico crítico |
| SocketIO Flask↔Worker | Redis DB5 | Compartir estado WebSocket |
| Estado tareas Celery | Redis DB4 | Resultados efímeros |

**Flujo resultante:**
```
Chat:
  Usuario → Flask → Redis DB3 (Celery broker) → celery-worker → Bedrock/MongoDB

ETL:
  celery-worker → RabbitMQ (etl_queue, durable) → etl-worker → Django/PostgreSQL
                                   ↓ fallo x3
                             etl_dead_letter queue (auditable, reintentable)
```

**Archivos afectados:**
- `worker/` → nuevo directorio (dos servicios dentro)
- `worker/Dockerfile`
- `worker/celery_app.py`
- `worker/tasks/chat_tasks.py`
- `worker/etl_consumer.py` → consumer RabbitMQ puro, sin Celery
- `docker-compose.yml` → servicios `celery-worker`, `etl-worker`, `rabbitmq`

**Pasos:**

**A) Worker Celery para chat:**
1. Crear directorio `worker/` con Dockerfile basado en `python:3.12-slim`
2. Instalar: `celery`, `redis`, `pika`, `boto3`, `pymongo`, `cryptography`, `PyYAML`, `numpy`
3. `celery_app.py`: configurar `broker=redis://redis:6379/3` y `backend=redis://redis:6379/4`
4. `chat_tasks.py`: mover lógica de `process_message_logic()` como `@celery.task`
5. Añadir en `docker-compose.yml` el servicio `celery-worker`:
   ```yaml
   celery-worker:
     command: celery -A celery_app worker -Q chat_queue --concurrency=4
   ```
6. Añadir servicio `flower` (`mher/flower`) en puerto 5555 para monitorización de tareas Celery

**B) Worker ETL con RabbitMQ:**
7. Añadir servicio `rabbitmq` en `docker-compose.yml`:
   ```yaml
   rabbitmq:
     image: rabbitmq:3-management
     ports:
       - "15672:15672"    # panel de gestión web
     environment:
       RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
       RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASS}
     volumes:
       - rabbitmq_data:/var/lib/rabbitmq   # persistencia en disco
     healthcheck:
       test: rabbitmq-diagnostics -q ping
   ```
8. Crear `worker/etl_consumer.py` con consumer `pika` que declare la cola durable con dead letter exchange:
   ```python
   channel.queue_declare(
       queue='etl_queue',
       durable=True,   # sobrevive a reinicios del broker
       arguments={
           'x-dead-letter-exchange': 'etl_dead_letter',
           'x-message-ttl': 86400000,   # 24h máximo en cola
       }
   )
   ```
9. Implementar ACK explícito: el mensaje solo se elimina de la cola tras confirmación de éxito en Django:
   ```python
   def process_etl(ch, method, properties, body):
       try:
           data = json.loads(body)
           result = execute_etl(data['user_id'], data['conversation_id'])
           if result['success']:
               ch.basic_ack(delivery_tag=method.delivery_tag)    # eliminar de cola
           else:
               ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # reintentar
       except Exception:
           ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)     # → dead letter
   ```
10. Cuando el `celery-worker` detecta que hay que hacer ETL, publica en RabbitMQ en lugar de encolar otra tarea Celery:
    ```python
    channel.basic_publish(
        exchange='',
        routing_key='etl_queue',
        body=json.dumps({'user_id': ..., 'conversation_id': ...}),
        properties=pika.BasicProperties(delivery_mode=2)   # persistir en disco
    )
    ```
11. Añadir en `docker-compose.yml` el servicio `etl-worker`:
    ```yaml
    etl-worker:
      build:
        context: ./backend
        dockerfile: worker/Dockerfile
      command: python etl_consumer.py
      depends_on:
        rabbitmq:
          condition: service_healthy
    ```

---

### #18 — Flask como gateway WebSocket ligero

**Servicio:** Flask | **Prioridad:** 🟢 NUEVO

**Dependencia:** Requiere #17 completado.

**Problema:** Con el Worker activo, Flask solo gestiona conexiones WebSocket: recibe el mensaje, valida, encola en Redis y devuelve typing. Flask necesita Redis como message queue compartida con el Worker para emitir respuestas.

**Archivos afectados:**
- `flask-services/src/routes/__init__.py` → configuración SocketIO
- `flask-services/src/routes/sockets_events.py` → `handle_chat_message()`
- `flask-services/src/app.py`

**Pasos:**
1. Cambiar `async_mode` de Flask-SocketIO a `'eventlet'` si no está configurado
2. Añadir `message_queue=redis://redis:6379/5` en la inicialización de SocketIO
3. En `handle_chat_message()`: encolar con `process_chat_message.delay()` en lugar de llamar `process_message_logic()`
4. Guardar `task.id → sid` en Redis para que el Worker sepa a quién notificar
5. El Worker emite `chat_response` por el mismo SocketIO compartido vía Redis DB5

---

### #19 — Endpoint de reintento manual de ETL vía RabbitMQ

**Servicio:** Flask | **Prioridad:** 🟢 NUEVO

**Dependencia:** Requiere #17 completado (RabbitMQ activo).

**Problema:** Cuando la ETL falla definitivamente y va a la dead letter queue, no hay mecanismo de reintento desde el frontend. Un endpoint HTTP permite al médico o al sistema republicar el mensaje desde la dead letter queue a la cola principal.

**Archivos afectados:**
- `flask-services/src/routes/chat_routes.py` → nuevo endpoint
- `worker/etl_consumer.py` → lógica de republicación desde dead letter

**Pasos:**
1. Añadir `POST /conversation/<conversation_id>/etl/retry` en `chat_routes.py`
2. Validar JWT del usuario antes de publicar
3. Publicar directamente en `etl_queue` de RabbitMQ con `delivery_mode=2` (persistente):
   ```python
   channel.basic_publish(
       exchange='',
       routing_key='etl_queue',
       body=json.dumps({'user_id': ..., 'conversation_id': ..., 'reason': 'manual_retry'}),
       properties=pika.BasicProperties(delivery_mode=2)
   )
   ```
4. Devolver `202 Accepted` con `{status: 'queued'}`
5. Añadir `GET /conversation/<conversation_id>/etl/status` que consulte si la conversación tiene ETL pendiente o en dead letter (leyendo de Mongo/Postgres)

---

### #20 — Caché Redis de resultados ETL

**Servicio:** ETL Worker | **Prioridad:** 🟢 NUEVO

**Dependencias:** Requiere #4 (cifrado MongoDB) y #17 (ETL Worker con RabbitMQ) completados.

**Problema:** Si Django falla durante la ETL y RabbitMQ reencola el mensaje, el `etl-worker` vuelve a llamar a Claude para generar el resumen médico, gastando tokens innecesariamente. Cachear el resultado procesado en Redis permite reintentar el envío a Django sin repetir la llamada a Bedrock.

**Archivos afectados:**
- `worker/etl_consumer.py`
- `flask-services/src/services/process_data/etl_runner.py`

**Pasos:**
1. En `etl_consumer.py`, antes de llamar a `process_medical_data()`: consultar `cache_key = etl:result:{user_id}:{conversation_id}`
2. Si existe en Redis: usar el dato cacheado directamente para enviar a Django y hacer `basic_ack`
3. Si no existe: llamar a `process_medical_data()` (que llama a Claude) y cachear con TTL 3600s
4. Tras envío exitoso a Django: borrar la clave de caché con `redis.delete(cache_key)` y hacer `basic_ack`
5. Si falla el envío a Django: hacer `basic_nack(requeue=True)` — RabbitMQ reencola; la caché evita repetir la llamada a Bedrock en el siguiente intento

---

## Bloque 4 — Experiencia, calidad y rendimiento

### #21 — Reorganización DBs Redis por función

**Servicio:** Ambos | **Prioridad:** ⚪ MEJORA

**Problema:** Redis usa DB0 y DB2 actualmente. Con Celery (solo chat) y SocketIO compartido se necesitan DBs adicionales bien organizadas para poder hacer `FLUSHDB` selectivo sin afectar otras funciones. La ETL ya no usa Redis como broker — usa RabbitMQ — lo que libera DBs para otros usos.

**Archivos afectados:**
- `flask-services/src/data/connect.py`
- `django_services/config/settings.py`
- `docker-compose.yml` → variables de entorno `REDIS_DB`

**Pasos:**

| DB | Uso |
|----|-----|
| DB0 | Sesiones Django y caché general |
| DB1 | Blacklist JWT de Django (mover desde DB0) |
| DB2 | Contexto conversacional Flask (`CHAT_REDIS_DB_CONTEXT`) |
| DB3 | Celery broker — **solo mensajes de chat** (no ETL) |
| DB4 | Celery results (estado de tareas de chat) |
| DB5 | SocketIO message queue Flask↔celery-worker (nuevo) |
| DB6 | Rate limiting WebSocket, caché sistema experto (#38) y caché ETL Bedrock (#20) |

Actualizar todas las referencias en `connect.py` y `settings.py`.

---

### #22 — Content-Security-Policy en Nginx

**Servicio:** Nginx | **Prioridad:** 🟡 IMPORTANTE

**Problema:** `nginx.conf` tiene `X-Frame-Options` y `X-XSS-Protection` pero no `Content-Security-Policy`. Sin CSP, un XSS exitoso puede exfiltrar datos clínicos a dominios externos sin restricción.

**Archivos afectados:**
- `nginx/nginx.conf`

**Pasos:**
1. Añadir en el bloque `server`:
   ```nginx
   add_header Content-Security-Policy "default-src 'self'; connect-src 'self' wss://api.medcheck.com; script-src 'self'; style-src 'self' 'unsafe-inline'";
   ```
2. Añadir bloque `server listen 443 ssl` con certificados Let's Encrypt de Certbot
3. Añadir redirección `301` de HTTP a HTTPS en el bloque `listen 80`
4. Verificar que el bloque HTTPS ya existe — el `nginx.conf` actual solo tiene `listen 80`

---

### #23 — Ampliar casos clínicos del sistema experto

**Servicio:** Flask | **Prioridad:** 🟡 IMPORTANTE

**Problema:** Solo existen 3 casos clínicos (ansiedad, cefalea, alcohol). Cualquier otro síntoma cae a `fallback_ai` con confianza `0.0` dependiendo completamente del LLM sin respaldo de reglas clínicas.

**Archivos afectados:**
- `flask-services/src/services/expert_system/rules/cases/` → nuevos YAML
- `flask-services/src/services/expert_system/rules/shared/emergency.yaml`

**Pasos:**
1. Añadir `fever_case.yaml`: fiebre/infección respiratoria (síntoma más frecuente en entornos laborales)
2. Añadir `back_pain_case.yaml`: dolor lumbar/muscular
3. Añadir `gastro_case.yaml`: náuseas, vómitos, dolor abdominal
4. Añadir `fatigue_case.yaml`: fatiga extrema, agotamiento
5. Cada YAML debe seguir la estructura existente: `case_id`, `intent_keywords`, `required_fields`, `tree`, `advice`
6. Revisar `emergency.yaml` para añadir red flags específicas de los nuevos casos

---

### #24 — Token WebSocket en primer mensaje en lugar de query param

**Servicio:** Flask | **Prioridad:** 🟡 IMPORTANTE

**Dependencia:** Requiere #10 completado.

**Problema:** El token JWT se pasa como `?token=xxx` en la URL de conexión WebSocket. Queda expuesto en logs de Nginx, logs del servidor y en el historial del navegador.

**Archivos afectados:**
- `flask-services/src/routes/sockets_events.py` → `handle_connect()`
- `frontend` → socket.io connection

**Pasos:**
1. En `handle_connect()`: permitir conexión sin token, emitir `connection_pending`
2. Añadir nuevo evento WebSocket `'authenticate'` que reciba `{token}` en el primer mensaje
3. En `handle_authenticate()`: validar token, registrar en Redis `ws:auth:{sid}`, emitir `connection_success`
4. Si en 10 segundos no llega `'authenticate'`: desconectar el SID automáticamente
5. En el frontend: tras conectar, emitir inmediatamente `socket.emit('authenticate', {token})`

---

### #25 — Evento triage_escalation en WebSocket

**Servicio:** Flask | **Prioridad:** ⚪ MEJORA

**Problema:** Cuando el nivel de triaje escala de Leve a Moderado o Severo durante la conversación, el frontend solo se entera si el usuario lee el texto de la respuesta.

**Archivos afectados:**
- `flask-services/src/routes/sockets_events.py` → `handle_chat_message()`
- `flask-services/src/services/chatbot/application/chat_turn_service.py`

**Pasos:**
1. En `handle_chat_message()`: comparar `triage_level` anterior (del contexto Redis) con `triage_final`
2. Si escala: emitir evento `'triage_escalation'` con `{previous, current, requires_attention: bool}`
3. Emitir antes de `'chat_response'` para que el frontend muestre la alerta primero
4. El frontend muestra modal/banner de alerta con el nivel de urgencia actualizado

---

### #26 — Respuesta de origen visible para el usuario (response_source)

**Servicio:** Flask | **Prioridad:** ⚪ MEJORA

**Problema:** El payload ya devuelve `response_source` (`'llm'`, `'expert'`, `'hybrid'`) pero el frontend probablemente no lo usa. Mostrar el origen de cada respuesta es un requisito de transparencia del AI Act para sistemas de IA de alto riesgo.

**Archivos afectados:**
- `frontend` → componente de mensaje del chat

**Pasos:**
1. El backend ya devuelve `response_source` en cada `chat_response` — no requiere cambios en Flask
2. Frontend: mostrar indicador visual en cada mensaje (ej: `'Protocolo clínico'` vs `'IA asistida'`)
3. No exponer detalles técnicos al usuario, solo una etiqueta comprensible
4. Documentar en el TFG como medida de cumplimiento AI Act artículo 13 (transparencia)

---

### #27 — Optimizar prompt INITIAL_PROMPT — reducir tokens

**Servicio:** Flask | **Prioridad:** ⚪ MEJORA

**Problema:** `INITIAL_PROMPT` tiene más de 600 palabras y se envía en cada turno. Consumo innecesario de tokens en cada llamada a Bedrock.

**Archivos afectados:**
- `flask-services/src/services/chatbot/application/chat_turn_service.py` → `INITIAL_PROMPT`
- `flask-services/src/services/chatbot/bedrock_claude.py` → `call_claude()`

**Pasos:**
1. Separar `INITIAL_PROMPT` en: `SYSTEM_PROMPT` (instrucciones fijas, ~100 palabras) y `CONTEXT_TEMPLATE` (datos dinámicos del turno)
2. Usar el parámetro `system` de la API Bedrock para el system prompt — se gestiona aparte de los tokens de usuario
3. En `_format_context_prompt()`: solo inyectar datos clínicos del turno actual, no repetir instrucciones generales
4. Estimación de ahorro: ~400 tokens/turno × 500 consultas/día × $0.00025/1K = ~$1.50/día

---

### #28 — Mocks de AWS en tests unitarios

**Servicio:** Flask | **Prioridad:** ⚪ MEJORA

**Problema:** Los tests que involucran Claude o Comprehend Medical hacen llamadas reales a AWS para pasar. Eso es caro, lento e inestable en CI.

**Archivos afectados:**
- `flask-services/tests/test_chat_flow_etl_integration.py`
- `flask-services/tests/test_llm_first_controller.py`
- `flask-services/tests/test_etl_runner.py`

**Pasos:**
1. Instalar `moto[bedrock]` para mocks de Bedrock y Comprehend Medical
2. Añadir `@mock.patch('services.chatbot.bedrock_claude.boto3.client')` en tests que llamen a Claude
3. Añadir `@mock.patch('services.chatbot.comprehend_medical.boto3.client')` en tests de entidades
4. Crear fixtures de respuestas mock realistas para Claude y Comprehend en `conftest.py`
5. Configurar CI/CD para ejecutar tests sin credenciales AWS

---

## Bloque 5 — Infraestructura Nginx

> *(Bloque adicional; la mejora #22 cubre CSP. Este bloque puede ampliarse con mejoras de hardening de Nginx adicionales según evolucione el proyecto.)*

---

## Bloque 6 — Sistema experto avanzado

*(Bloque ampliado con #23 en Bloque 4 y las mejoras de calidad clínica en Bloque 8.)*

---

## Bloque 7 — Seguridad avanzada de WebSocket

*(Bloque ampliado con #24 en Bloque 4.)*

---

## Bloque 8 — Calidad clínica y experiencia (NUEVO)

### #29 — Memoria longitudinal entre conversaciones

**Servicio:** Flask (+ MongoDB + embeddings) | **Prioridad:** 🔴 CRÍTICO

**Impacto:** Máximo — reduce repetición, mejora diagnóstico y continuidad.

**Archivos probables:**
- `ConversationContextService`
- Lógica de embeddings (`_embed_text()`)
- Colección `conversation_embeddings`
- `_format_context_prompt()`

**Pasos:**
1. Al inicio de cada turno: construir query semántica con el mensaje del usuario + síntomas clave del snapshot actual
2. Buscar en MongoDB otras conversaciones del mismo `user_id`/`patient_id` por similitud (top_k 5–10, con score mínimo)
3. Inyectar los resultados en `global_semantic_context` (no en `semantic_context`, que es "local")
4. Guardar también el "por qué" del match (`timestamp` + resumen corto) para trazabilidad
5. Límite de tokens: recorte a 800–1200 tokens máximo de historial global

**Dependencias:**
- Encaja con la infraestructura existente (embeddings + Mongo + campos listos)
- Si implementas Worker (#17), esto puede correr en background para no bloquear

**Criterio de aceptación:**
- En conversación nueva, el bot menciona contexto previo relevante ("Hace 3 semanas comentaste X…") solo si hay match semántico > umbral definido

---

### #30 — Detección de contradicciones intra-conversación

**Servicio:** Flask (sistema experto + snapshot) | **Prioridad:** 🔴 CRÍTICO

**Impacto:** Alto — mejora triage y reduce errores.

**Archivos probables:**
- `pain_utils.py`
- `snapshot/context` (`context_snapshot`)
- Orquestación del turno
- Prompt formatter

**Pasos:**
1. Añadir `ContradictionDetector` que compare:
   - Campos estructurados (fiebre, dolor, duración, etc.) entre `context_snapshot_anterior` vs `context_snapshot_actual`
   - Hechos críticos (fiebre sí/no, dolor pecho sí/no, disnea, síncope…)
2. Regla para dolor: priorizar valor más reciente (y opcionalmente guardar tendencia, no el máximo)
3. Emitir al prompt una sección fija `inconsistencies: [...]` con mensajes tipo: `"Antes dijo A, ahora dice B"`
4. Si la contradicción toca red flags: subir sensibilidad (forzar pregunta de aclaración o escalar revisión)

**Dependencias:**
- Complementa plan base #23 (más casos clínicos) y #25 (evento `triage_escalation`)

**Criterio de aceptación:**
- Si el usuario cambia "no fiebre" → "39°C", el sistema lo detecta y el LLM lo ve explícito en el contexto

---

### #31 — Pregunta de cierre post-triaje

**Servicio:** Flask | **Prioridad:** 🟡 IMPORTANTE

**Impacto:** Alto en comunicación clínica, baja complejidad.

**Archivos afectados:**
- `finalization_service.py` (ya existente)

**Pasos:**
1. Cuando `action="advise"`: no finalizar "funcionalmente" sin una pregunta de confirmación
2. Añadir un estado `awaiting_confirmation = true` y solo cerrar por:
   - Respuesta del usuario ("ok", "no", "gracias", etc.), o
   - Timeout de inactividad (ver #35)
3. Guardar esa última respuesta en Mongo/Postgres para completar ETL

**Dependencias:**
- Va de la mano con mejora #14 (ETL prematura): evita cerrar antes de que el usuario lea/responda

---

### #32 — Red flags con contexto temporal e intensidad

**Servicio:** Flask (sistema experto) | **Prioridad:** 🟡 IMPORTANTE

**Impacto:** Reduce falsos positivos/negativos en emergencia.

**Archivos afectados:**
- `emergency.yaml`
- `emergency_guard.py`

**Pasos:**
1. Extender schema YAML: añadir campos `tense_guard`, `intensity_guard`, `context_window`
2. En `emergency_guard.py`:
   - Detectar marcadores de pasado ("tuve", "la semana pasada", "antes", "ya se me pasó")
   - Detectar negaciones ("no", "nunca", "sin")
   - Aplicar `context_window` (n palabras alrededor) para validar que es afirmación presente
3. Mantener compatibilidad: si no hay guards → comportamiento actual

**Criterio de aceptación:**
- `"Tuve dolor de pecho la semana pasada, ya resuelto"` → NO dispara emergencia
- `"Molestia en el pecho ahora mismo"` → SÍ dispara si `tense_guard: present`

---

### #33 — Modo "segunda opinión" para médico

**Servicio:** Django + Flask | **Prioridad:** 🟢 NUEVO

**Impacto:** Producto y valor real para entorno clínico/empresa.

**Archivos afectados:**
- Endpoint Flask nuevo
- `_format_context_prompt()`
- Acceso a `PatientHistoryEntry` (PostgreSQL)

**Pasos:**
1. Añadir rol `doctor` al flujo (token + permisos)
2. Crear endpoint Flask: `POST /doctor/patient/<id>/ask`
3. Construir contexto estructurado: historial último mes, medicación, alergias, episodios, triage previos
4. Prompt específico: respuesta en formato estructurado (bullets + tabla simple)
5. Respetar `DoctorPatientRelation` e `is_data_validated`

**Dependencias:**
- Implementar después de reforzar seguridad del plan base (#1–#6 y #2 AuditLog), porque expone datos sensibles

---

### #34 — Confianza visible en el consejo final

**Servicio:** Flask | **Prioridad:** ⚪ MEJORA

**Impacto:** Transparencia y mejor UX clínica.

**Archivos afectados:**
- Donde se construye el mensaje final (`advise`)
- `triage_policy.yaml` o plantillas de advice

**Pasos:**
1. Usar `confidence` de `ExpertDecision` y mapear a buckets:
   - Alta: ≥ 0.85
   - Media: 0.70–0.84
   - Baja: 0.65–0.69
2. Plantillas diferenciadas por nivel y confianza (`high_confidence`, `low_confidence`)
3. Si confianza baja: añadir recomendación explícita de "si empeora o dudas → presencial"

**Criterio de aceptación:**
- Advice cambia de tono según confianza sin cambiar el nivel de triaje

---

### #35 — Aviso visible de timeout por inactividad

**Servicio:** Flask + WebSocket + Frontend | **Prioridad:** 🔴 CRÍTICO

**Impacto:** Evita pérdida de datos y frustración del usuario.

**Archivos afectados:**
- `etl_runner.py` (timer)
- `sockets_events.py` (evento WS)
- Frontend listener

**Pasos:**
1. Programar warning a los 12 minutos: emitir `session_warning` con `{seconds_left: 180}`
2. Si el usuario responde: reset de timers
3. Mantener cierre a los 15 min como está hoy (y disparar ETL)
4. Mensaje sugerido: `"Se cerrará en 3 min… ¿Algo más que añadir?"`

**Dependencias:**
- Encaja con plan base #14 (finalización) y #18 (si implementas Worker, el WS queda más limpio)

---

### #36 — Detección de idioma + respuesta multilingüe

**Servicio:** Flask | **Prioridad:** ⚪ MEJORA

**Impacto:** Real en entornos universitarios/empresa multiculturales.

**Archivos afectados:**
- `input_validate.py`
- `INITIAL_PROMPT`

**Pasos:**
1. Añadir `langdetect` (o alternativa) y detectar idioma por turno (con caching por conversación)
2. Guardar `detected_language` en contexto
3. Añadir instrucción al prompt: `"Responde en el mismo idioma que el usuario"`
4. Ajustar validaciones "español-only" para que no rompan entradas en inglés/catalán/euskera: no bloquear por caracteres ni stopwords fijas

---

### #37 — Resumen visible al finalizar

**Servicio:** Flask + Worker/ETL + WebSocket | **Prioridad:** ⚪ MEJORA

**Impacto:** Cierre claro para paciente, reduce confusión.

**Archivos afectados:**
- `medical_data.py` (`summary` ya existe)
- Donde termina ETL (callback)
- `sockets_events.py`

**Pasos:**
1. Tras ETL exitosa: emitir WS `conversation_summary` con texto "patient-friendly"
2. Si ETL falla: emitir `conversation_summary_failed` con fallback ("no se pudo generar…")
3. Guardar resumen `patient_view` separado del resumen clínico para evitar lenguaje técnico

**Dependencias:**
- Si ya implementas caché de ETL (#20), esto queda más robusto

---

### #38 — Caché de sistema experto para casos idénticos

**Servicio:** Flask + Redis | **Prioridad:** ⚪ MEJORA

**Impacto:** Rendimiento/coste, bajo riesgo si se acota bien.

**Dependencias:** Requiere #21 (reorganización Redis DBs) completado.

**Archivos afectados:**
- `ExpertOrchestrator`
- Redis connect

**Pasos:**
1. Normalizar mensaje: lower, trim, quitar puntuación básica (opcional: lematización ligera)
2. `cache_key = expert:{hash(normalizado)}`
3. TTL: 300 segundos
4. Cachear **solo**: decisión del sistema experto + `confidence` + `triage_level` + `action`
5. **Nunca cachear** la salida final del LLM

---

## Resumen de archivos más afectados

| Archivo | Mejoras que lo modifican |
|---------|--------------------------|
| `flask-services/src/routes/sockets_events.py` | #9, #10, #18, #24, #25, #35 |
| `flask-services/src/data/connect.py` | #5, #9, #10, #21 |
| `flask-services/src/services/chatbot/application/finalization_service.py` | #14, #31 |
| `flask-services/src/services/chatbot/application/chat_turn_service.py` | #25, #27 |
| `django_services/users/models.py` | #2, #3 |
| `django_services/users/views.py` | #1, #2, #6, #8, #15 |
| `django_services/config/settings.py` | #5, #13, #16, #21 |
| `docker-compose.yml` | #5, #12, #17, #21 |
| `worker/etl_consumer.py` | #17, #19, #20 |
| `worker/celery_app.py` + `worker/tasks/chat_tasks.py` | #17, #18 |
| `emergency.yaml` + `emergency_guard.py` | #32 |
