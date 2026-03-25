# Plan de Mejoras Técnicas — Chatbot de Triaje Médico Hipo

**TFG · Ciclo actual sobre arquitectura Flask + Django + MongoDB + PostgreSQL + Redis**  
**43 mejoras · plan vivo por fases · migración a microservicios pospuesta**

---

## Estado actual del plan

- **Fase 0 cerrada:** `#43` resuelta e implementada en el repositorio el **19 de marzo de 2026**.
- **Fase 1 cerrada:** `#1`, `#5`, `#6`, `#8`, `#9`, `#10`, `#11`, `#12`, `#13`, `#16`, `#22` y `#24` implementadas en el repositorio el **19 de marzo de 2026**.
- **Ciclo actual:** estabilización y securización de la arquitectura existente `flask-services` + `django_services`.
- **Siguiente foco operativo:** Fase 2 (protección de datos y trazabilidad) y, a continuación, Fase 3 (robustez funcional).
- **Fuera de alcance del ciclo actual:** `#17`, `#18`, `#19`, `#20`, `#39`, `#40`, `#41`, `#42` quedan pospuestas a la Fase 6.
- **Reclasificación funcional:** `#29`, `#30` y `#35` dejan de tratarse como bloqueantes iniciales y pasan a fases posteriores de calidad funcional.



---

## Índice rápido

| # | Mejora | Servicio | Estado / Prioridad |
|---|--------|----------|--------------------|
| 1 | Firma HMAC-SHA256 en peticiones Flask → Django | Ambos | ✅ RESUELTO · Fase 1 |
| 2 | Tabla AuditLog con firma criptográfica | Django | 🔴 CRÍTICO |
| 3 | Cifrado de campos clínicos en PostgreSQL | Django | 🔴 CRÍTICO |
| 4 | Cifrado de mensajes clínicos en MongoDB | Flask | 🔴 CRÍTICO |
| 5 | Autenticación y TLS en Redis | Ambos | ✅ RESUELTO · Fase 1 |
| 6 | Tokens de acceso firmados para endpoints sensibles | Django | ✅ RESUELTO · Fase 1 |
| 7 | Corrección de la clase Encryption de Flask | Flask | 🟡 IMPORTANTE |
| 8 | Eliminar CORS wildcard en métodos options() manuales | Django | ✅ RESUELTO · Fase 1 |
| 9 | Rate limiting en WebSocket por usuario | Flask | ✅ RESUELTO · Fase 1 |
| 10 | Mover AUTHENTICATED_USERS_BY_SID a Redis | Flask | ✅ RESUELTO · Fase 1 |
| 11 | Validación de variables de entorno críticas al arranque | Flask | ✅ RESUELTO · Fase 1 |
| 12 | Health check endpoints en Flask y Django | Ambos | ✅ RESUELTO · Fase 1 |
| 13 | Throttling en endpoints de autenticación Django | Django | ✅ RESUELTO · Fase 1 |
| 14 | Rectificación de detect_finalization — ETL prematura | Flask | 🟡 IMPORTANTE |
| 15 | Corrección N+1 queries en PatientSerializer | Django | 🟡 IMPORTANTE |
| 16 | Reducir ACCESS_TOKEN_LIFETIME de JWT a 15 minutos | Django | ✅ RESUELTO · Fase 1 |
| 17 | Worker Celery (chat) + Worker ETL con RabbitMQ | Nuevo | 🟢 NUEVO |
| 18 | Flask como gateway WebSocket ligero | Flask | 🟢 NUEVO |
| 19 | Endpoint de reintento manual de ETL vía RabbitMQ | Flask | 🟢 NUEVO |
| 20 | Caché Redis de resultados ETL | ETL Worker | 🟢 NUEVO |
| 21 | Reorganización DBs Redis por función | Ambos | ⚪ MEJORA |
| 22 | Content-Security-Policy en Nginx | Nginx | ✅ RESUELTO · Fase 1 |
| 23 | Ampliar casos clínicos del sistema experto | Flask | 🟡 IMPORTANTE |
| 24 | Token WebSocket en primer mensaje en lugar de query param | Flask | ✅ RESUELTO · Fase 1 |
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
| 39 | Migración Flask → FastAPI gateway WebSocket (5000) | Gateway | 🔴 CRÍTICO |
| 40 | Nuevo microservicio ai-service (5001) | ai-service | 🟢 NUEVO |
| 41 | Nuevo microservicio expert-service (5002) | expert-service | 🟢 NUEVO |
| 42 | Modo consulta médica libre con escalado automático a triaje | Gateway + ai-service + expert-service | 🟢 NUEVO |
| 43 | Corrección ETL → Django: 400 Bad Request por validación rota | Django + Flask | ✅ RESUELTO · Fase 0 |

---

## Fases de trabajo vigentes

### Fase 0 — Desbloqueo inmediato

- **Estado:** ✅ Completada
- **Objetivo:** desbloquear la persistencia ETL hacia Django/PostgreSQL
- **Incluye:** `#43`
- **Resultado cerrado:** se corrigió la validación de campos vacíos, la coerción de `pain_scale` y la alineación de `FLASK_API_KEY`

### Fase 1 — Seguridad y sesión en la arquitectura actual

- **Estado:** ✅ Completada
- **Objetivo:** cerrar riesgos operativos y de autenticación sin cambiar de arquitectura
- **Incluye:** `#1`, `#5`, `#8`, `#13`, `#6`, `#10`, `#24`, `#16`, `#9`, `#11`, `#12`, `#22`
- **Regla de ejecución:** `#16` no empieza hasta cerrar `#24`
- **Resultado cerrado:** se endureció el transporte interno Flask → Django con firma HMAC y timestamp, Redis quedó protegido con contraseña y clientes autenticados, el WebSocket pasó a autenticación explícita con sesión en Redis y rate limiting, Django añadió throttling, tokens firmados para historial médico, `ACCESS_TOKEN_LIFETIME=15m`, y ambos servicios exponen `/health`.
- **Hardening adicional aplicado en esta fase:** se eliminaron fallbacks inseguros de identidad aportada por cliente en rutas críticas de Flask, se cerró el modo WebSocket anónimo y el frontend se alineó con el nuevo contrato WS y con el historial firmado.
- **Verificación registrada:** `python -m unittest backend\\flask-services\\tests\\test_medical_data_processor.py` → OK. `python backend\\django_services\\manage.py test users.tests` quedó preparado pero no pudo ejecutarse en este entorno por ausencia de PostgreSQL accesible en `localhost:5432`.

### Fase 2 — Protección de datos y trazabilidad

- **Estado:** Pendiente
- **Objetivo:** cifrado en reposo y trazabilidad clínica auditable
- **Incluye:** `#2`, `#3`, `#4`, `#7`
- **Regla de ejecución:** `#2` va antes de `#3` y `#4`

### Fase 3 — Corrección funcional y robustez

- **Estado:** Pendiente
- **Objetivo:** estabilizar el flujo conversacional y reducir fallos funcionales
- **Incluye:** `#14`, `#15`, `#31`, `#35`, `#21`

### Fase 4 — Calidad clínica y experiencia

- **Estado:** Pendiente
- **Objetivo:** mejorar capacidad clínica, transparencia y UX sin re-arquitectura
- **Incluye:** `#23`, `#32`, `#30`, `#29`, `#25`, `#26`, `#34`, `#36`, `#37`, `#38`, `#27`, `#28`

### Fase 5 — Funcionalidad nueva sobre arquitectura actual

- **Estado:** Pendiente
- **Objetivo:** añadir valor funcional sin introducir la migración a microservicios
- **Incluye:** `#33`

### Fase 6 — Epic separada de arquitectura

- **Estado:** Pospuesta
- **Objetivo:** rediseño arquitectónico solo cuando el sistema actual esté estable y existan métricas que justifiquen la partición
- **Incluye:** `#17`, `#18`, `#19`, `#20`, `#39`, `#40`, `#41`, `#42`

### Dependencias críticas entre mejoras

- `#2` (AuditLog) → antes de `#3`, `#4` (cualquier modificación de datos clínicos)
- `#4` (cifrado MongoDB) → antes de `#20` (caché ETL Redis)
- `#10` (Redis auth WS) → antes de `#24` (token en primer mensaje)
- `#16` (reducir token lifetime) → requiere cambios en frontend para renovación automática
- `#21` (reorganización Redis) → antes de `#38` (caché sistema experto)
- `#35` (timeout WS) → coordinado con `#31` (cierre post-triaje)
- `#17` (Worker Celery + ETL Worker RabbitMQ) → antes de `#18`, `#19`, `#20`
- `#39` (gateway FastAPI) → antes de `#40`, `#41`, `#42` (los microservicios dependen del gateway)
- `#17` (Worker Celery + ETL Worker) → antes de `#40` (ai-service hereda la integración con Celery)
- `#40` + `#41` (ai-service y expert-service) → antes de `#42` (modo consulta necesita ambos servicios activos)
- `#32` (red flags con contexto) → antes de `#42` (el escalado a triaje reutiliza EmergencyGuard mejorado)
- `#43` (fix ETL 400) → ✅ cerrada en Fase 0; no bloquea ya el inicio de Fase 1

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

---

## Bloque 9 — Migración a FastAPI y separación en microservicios

> **Contexto arquitectural.** El monolito Flask actual mezcla WebSocket, lógica de IA, sistema experto y orquestación en el mismo proceso. Este bloque lo divide en tres servicios autónomos siguiendo la arquitectura propuesta:
>
> ```
> gateway (5000) — FastAPI WebSocket
> ├── Autenticación JWT
> ├── Rate limiting
> ├── Orquesta llamadas a ai-service y expert-service
> └── Devuelve respuesta al frontend
>
>         ▼                    ▼
> ai-service (5001)    expert-service (5002)
> ├── Bedrock/Claude   ├── ExpertOrchestrator
> ├── Comprehend       ├── YAML rules
> ├── RAG/embeddings   ├── EmergencyGuard
> └── ConversContext   └── TriageClassification
>
>         ▼
> etl-worker — Celery/RabbitMQ (ya cubierto en #17)
> ```

---

### #39 — Migración Flask → FastAPI como gateway WebSocket (5000)

**Servicio:** Gateway | **Prioridad:** 🔴 CRÍTICO

**Problema:** Flask-SocketIO tiene limitaciones de rendimiento bajo carga concurrente (GIL, threads síncronos). FastAPI con Starlette WebSockets es ASGI nativo: soporta `async/await` real, lo que elimina el bloqueo en llamadas a Bedrock, Redis y los microservicios internos. Además, FastAPI genera OpenAPI automáticamente y su sistema de dependencias (Depends) simplifica la validación JWT.

**Archivos afectados:**
- `gateway/` → nuevo directorio (reemplaza `flask-services/`)
- `gateway/main.py` → entrypoint FastAPI con Uvicorn
- `gateway/routers/ws_router.py` → WebSocket handler (reemplaza `sockets_events.py`)
- `gateway/routers/http_router.py` → endpoints HTTP (health, retry ETL, etc.)
- `gateway/middleware/auth.py` → JWT validation como FastAPI Dependency
- `gateway/middleware/rate_limit.py` → SlowAPI rate limiter
- `gateway/services/orchestrator.py` → llama a ai-service y expert-service vía httpx async
- `docker-compose.yml` → renombrar servicio `flask` → `gateway`, cambiar imagen base

**Pasos:**
1. Crear `gateway/` con estructura:
   ```
   gateway/
   ├── main.py
   ├── Dockerfile
   ├── requirements.txt
   ├── routers/
   │   ├── ws_router.py
   │   └── http_router.py
   ├── middleware/
   │   ├── auth.py
   │   └── rate_limit.py
   └── services/
       └── orchestrator.py
   ```
2. Instalar: `fastapi`, `uvicorn[standard]`, `websockets`, `httpx`, `slowapi`, `python-jose[cryptography]`, `redis[hiredis]`
3. En `main.py`: crear app FastAPI con middleware CORS, montar routers, conectar al arranque a Redis
4. En `ws_router.py`: implementar `WebSocket` handler con el mismo protocolo de eventos que Flask-SocketIO (`chat_message`, `authenticate`, `triage_escalation`, etc.). Nota: FastAPI WebSockets usa `await websocket.send_json()` en lugar de `socketio.emit()`
5. En `middleware/auth.py`: `async def get_current_user(token: str, redis: Redis)` — validar JWT, verificar blacklist en Redis DB1
6. En `middleware/rate_limit.py`: `slowapi` con `Limiter(key_func=get_remote_address)`, aplicar `@limiter.limit("20/minute")` en el endpoint WS
7. En `services/orchestrator.py`: cliente `httpx.AsyncClient` con base URLs de ai-service (5001) y expert-service (5002), con retry automático (`httpx-retry`)
8. En `http_router.py`: portar todos los endpoints HTTP del Flask actual (health, retry ETL, etc.)
9. En `docker-compose.yml`: añadir servicio `gateway` con `command: uvicorn main:app --host 0.0.0.0 --port 5000 --workers 2`
10. Migrar variables de entorno: `FLASK_*` → `GATEWAY_*` en `.env`
11. Actualizar Nginx: `proxy_pass http://gateway:5000` (sin cambio de puerto)

**Criterio de aceptación:**
- `ws://gateway:5000/ws` acepta conexiones y procesa el flujo completo de triaje end-to-end
- Los tests existentes de integración pasan con el nuevo gateway (adaptar fixtures de SocketIO → WebSocket nativo)

---

### #40 — Nuevo microservicio ai-service (5001)

**Servicio:** ai-service | **Prioridad:** 🟢 NUEVO

**Dependencia:** Requiere #39 (gateway FastAPI) completado.

**Problema:** La lógica de Bedrock/Claude, Comprehend Medical, RAG con embeddings y el contexto conversacional están acoplados al monolito Flask. Extraerlos a un servicio dedicado permite: escalar independientemente (más instancias si hay carga de IA), actualizar modelos sin afectar la lógica de triaje, y hacer testing unitario de la IA de forma aislada.

**Archivos afectados:**
- `ai-service/` → nuevo directorio
- `ai-service/main.py` → FastAPI app en puerto 5001
- `ai-service/routers/inference.py` → endpoints de inferencia
- `ai-service/services/bedrock_claude.py` → extraído de `flask-services/`
- `ai-service/services/comprehend_medical.py` → extraído de `flask-services/`
- `ai-service/services/conversation_context.py` → `ConversationContextService` extraído
- `ai-service/services/embeddings.py` → lógica RAG/embeddings extraída
- `docker-compose.yml` → nuevo servicio `ai-service`

**Pasos:**
1. Crear `ai-service/` con estructura similar a gateway:
   ```
   ai-service/
   ├── main.py
   ├── Dockerfile
   ├── requirements.txt
   └── routers/
       └── inference.py
   └── services/
       ├── bedrock_claude.py
       ├── comprehend_medical.py
       ├── conversation_context.py
       └── embeddings.py
   ```
2. Instalar: `fastapi`, `uvicorn[standard]`, `boto3`, `pymongo`, `redis[hiredis]`, `numpy`, `cryptography`
3. Definir API interna (solo accesible desde la red Docker, sin exponer en Nginx):
   ```
   POST /inference/chat        → llama a Claude con contexto
   POST /inference/comprehend  → extrae entidades médicas
   POST /inference/embed       → genera embedding de un texto
   GET  /health                → verifica conectividad con Bedrock y MongoDB
   ```
4. Mover `bedrock_claude.py`, `comprehend_medical.py`, `ConversationContextService`, `embeddings.py` desde `flask-services/` a `ai-service/services/`
5. Adaptar imports (eliminar dependencias de Flask, usar solo `fastapi`, `boto3`, etc.)
6. En `gateway/services/orchestrator.py`: llamar a `POST http://ai-service:5001/inference/chat` con `httpx` async
7. En `docker-compose.yml`: añadir servicio `ai-service` con `command: uvicorn main:app --host 0.0.0.0 --port 5001 --workers 1` (sin exponer puerto al host)
8. La red Docker interna (`hipo_network`) permite comunicación gateway → ai-service sin pasar por Nginx
9. Secrets AWS (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`) solo presentes en `ai-service`, no en gateway

**Criterio de aceptación:**
- `POST http://ai-service:5001/inference/chat` devuelve respuesta de Claude correctamente desde el gateway
- `GET http://ai-service:5001/health` devuelve `{bedrock: ok, mongo: ok}`

---

### #41 — Nuevo microservicio expert-service (5002)

**Servicio:** expert-service | **Prioridad:** 🟢 NUEVO

**Dependencia:** Requiere #39 (gateway FastAPI) completado.

**Problema:** El sistema experto (`ExpertOrchestrator`, YAMLs de casos, `EmergencyGuard`, `TriageClassification`) está mezclado con Flask. Separarlo permite: cargarlo una sola vez en memoria al arranque (los YAMLs se parsean una vez), reiniciarlo sin afectar las conexiones WebSocket activas, y añadir nuevos casos clínicos sin redesplegar el gateway.

**Archivos afectados:**
- `expert-service/` → nuevo directorio
- `expert-service/main.py` → FastAPI app en puerto 5002
- `expert-service/routers/triage.py` → endpoints del sistema experto
- `expert-service/services/expert_orchestrator.py` → extraído de Flask
- `expert-service/services/emergency_guard.py` → extraído de Flask
- `expert-service/services/triage_classification.py` → extraído de Flask
- `expert-service/rules/` → directorio con YAMLs de casos (copiado de Flask)
- `docker-compose.yml` → nuevo servicio `expert-service`

**Pasos:**
1. Crear `expert-service/` con estructura:
   ```
   expert-service/
   ├── main.py
   ├── Dockerfile
   ├── requirements.txt
   ├── routers/
   │   └── triage.py
   ├── services/
   │   ├── expert_orchestrator.py
   │   ├── emergency_guard.py
   │   └── triage_classification.py
   └── rules/
       ├── cases/
       │   ├── ansiedad.yaml
       │   ├── cefalea.yaml
       │   └── ... (todos los YAMLs existentes)
       └── shared/
           └── emergency.yaml
   ```
2. Instalar: `fastapi`, `uvicorn[standard]`, `PyYAML`, `redis[hiredis]`
3. Definir API interna:
   ```
   POST /expert/evaluate        → ExpertOrchestrator.evaluate(snapshot) → ExpertDecision
   POST /expert/emergency-check → EmergencyGuard.check(message) → {is_emergency, matched_rules}
   GET  /expert/cases           → lista de casos clínicos activos (para debug/monitoring)
   GET  /health
   ```
4. En `main.py`: cargar todos los YAMLs al arranque con `@app.on_event("startup")` y mantenerlos en memoria (evitar re-parseo en cada request)
5. Mover `ExpertOrchestrator`, `EmergencyGuard`, `TriageClassification` desde `flask-services/` a `expert-service/services/`
6. Copiar directorio `rules/` completo a `expert-service/rules/`
7. En `gateway/services/orchestrator.py`: llamar a `POST http://expert-service:5002/expert/evaluate` en paralelo con `ai-service` usando `asyncio.gather()`
8. En `docker-compose.yml`: añadir servicio `expert-service` con `command: uvicorn main:app --host 0.0.0.0 --port 5002 --workers 1`
9. Añadir `volume` para montar `rules/` en caliente: permite actualizar YAMLs sin rebuild de imagen

**Criterio de aceptación:**
- `POST http://expert-service:5002/expert/evaluate` devuelve `ExpertDecision` válida con nivel de triaje y `confidence`
- Modificar un YAML de reglas y reiniciar solo `expert-service` no interrumpe las conexiones WebSocket del gateway

---

## Bloque 10 — Modo consulta médica libre

### #42 — Modo consulta médica libre con escalado automático a triaje

**Servicio:** Gateway + ai-service + expert-service | **Prioridad:** 🟢 NUEVO

**Dependencias:** Requiere #39, #40, #41 completados. Recomendado después de #32 (EmergencyGuard con contexto temporal).

**Problema/Motivación:** El chatbot actual solo funciona en modo triaje estructurado (protocolo SET). Sin embargo, muchos usuarios necesitan resolver dudas médicas sencillas sin iniciar un proceso de triaje completo ("¿Puedo tomar ibuprofeno con omeprazol?", "¿Cuánto dura normalmente un catarro?"). El modo consulta libre permite preguntas abiertas con IA, y si el `EmergencyGuard` del `expert-service` detecta síntomas de alarma en alguna respuesta del usuario, escala automáticamente al modo triaje activando el protocolo SET.

**Arquitectura del modo consulta:**

```
Usuario → gateway WebSocket
    │
    ├── [mode: consultation]
    │       ├── gateway envía mensaje a ai-service (chat libre, prompt diferente)
    │       └── gateway envía mensaje a expert-service /emergency-check (en paralelo)
    │               │
    │               ├── Sin red flags → respuesta de consulta libre al usuario
    │               └── Red flags detectadas → emitir 'mode_escalation' + activar modo triaje
    │
    └── [mode: triage]
            └── flujo SET existente (sin cambios)
```

**Archivos afectados:**
- `gateway/routers/ws_router.py` → gestión del campo `mode` en el estado de sesión
- `gateway/services/orchestrator.py` → lógica de bifurcación consultation vs. triage
- `ai-service/routers/inference.py` → nuevo endpoint `POST /inference/consult`
- `ai-service/services/bedrock_claude.py` → nuevo prompt `CONSULTATION_PROMPT`
- `expert-service/routers/triage.py` → `/expert/emergency-check` (ya definido en #41)
- Redis → nuevo campo `session_mode` en `ws:session:{sid}`
- Frontend → botón de toggle de modo + handler del evento `mode_escalation`

**Pasos:**

**A) Estado de modo en la sesión:**
1. Añadir campo `session_mode` en el hash Redis de sesión: valores `'consultation'` o `'triage'`
2. Al conectar: modo por defecto configurable por variable de entorno `DEFAULT_SESSION_MODE` (valor recomendado: `'consultation'`)
3. En `ws_router.py`: leer `session_mode` al procesar cada mensaje para bifurcar el flujo

**B) Nuevo endpoint de consulta en ai-service:**
4. En `ai-service/routers/inference.py`: añadir `POST /inference/consult` que use `CONSULTATION_PROMPT` en lugar de `INITIAL_PROMPT`
5. `CONSULTATION_PROMPT` debe:
   - Identificar al bot como asistente de salud informativo (no diagnóstico)
   - Responder preguntas médicas generales con lenguaje claro y sin alarmar
   - Incluir disclaimer: "Consulta a tu médico para decisiones clínicas"
   - Responder en el idioma del usuario (ver #36)
   - **No** seguir el protocolo SET ni preguntar por síntomas específicos salvo que sean relevantes

**C) Chequeo paralelo de emergencia:**
6. En `gateway/services/orchestrator.py`: para mensajes en modo `consultation`, lanzar en paralelo con `asyncio.gather()`:
   - `POST http://ai-service:5001/inference/consult` → respuesta libre
   - `POST http://expert-service:5002/expert/emergency-check` → análisis de red flags
7. Si `emergency-check` devuelve `{is_emergency: false}`: enviar respuesta de consulta libre al usuario
8. Si `emergency-check` devuelve `{is_emergency: true, matched_rules: [...]}`:
   - No enviar la respuesta de consulta libre
   - Emitir evento WebSocket `'mode_escalation'` con `{reason: matched_rules, new_mode: 'triage'}`
   - Cambiar `session_mode` a `'triage'` en Redis
   - Emitir como primer mensaje del modo triaje la pregunta inicial del protocolo SET

**D) Transición suave al modo triaje:**
9. Mensaje de escalado sugerido (configurable en `.env` o YAML):
   ```
   "He detectado síntomas que requieren una valoración más detallada.
    Voy a hacerte unas preguntas para asegurarme de que estás bien. ¿Empezamos?"
   ```
10. El usuario puede rechazar el escalado (responder "no", "estoy bien"): en ese caso mantener modo consulta pero registrar el evento de `escalation_declined` en MongoDB para auditoría

**E) Toggle manual de modo:**
11. Añadir evento WebSocket `'set_mode'` que reciba `{mode: 'triage' | 'consultation'}` desde el frontend
12. Actualizar `session_mode` en Redis al recibir el evento
13. Frontend: botón visible "Iniciar triaje" / "Volver a consulta" que emita `'set_mode'`

**F) Límites del modo consulta:**
14. El modo consulta también aplica rate limiting (#39 middleware): mismo límite de 20 mensajes/minuto
15. No persistir conversaciones de consulta en PostgreSQL (son informativas, no clínicas); sí en MongoDB para historial del usuario
16. Si la sesión lleva más de 20 mensajes en modo consulta sin escalado: sugerir al usuario consulta presencial (mensaje configurable)

**Criterio de aceptación:**
- Pregunta médica simple ("¿Puedo tomar ibuprofeno con omeprazol?") → responde en modo consulta sin activar triaje
- Mensaje con red flag ("tengo dolor de pecho y me falta el aire ahora mismo") → en modo consulta, escala automáticamente a triaje y emite `mode_escalation` antes de continuar
- El toggle manual `'set_mode'` cambia el modo correctamente y el siguiente mensaje ya sigue el flujo del nuevo modo

---

---

## Bloque 11 — Bug crítico: ETL → Django 400 Bad Request

### #43 — Corrección ETL → Django: 400 Bad Request por validación rota

**Estado:** ✅ RESUELTO  
**Fase:** Fase 0 — Desbloqueo inmediato  
**Fecha de cierre:** 19 de marzo de 2026

**Servicio:** Django + Flask | **Prioridad:** 🔴 CRÍTICO

**Resultado:** La regresión quedó corregida en el código base. La ETL ya normaliza `pain_scale`, acepta campos vacíos opcionales en Django y usa `FLASK_API_KEY` explícita para el token de integración interno.

**Cambios aplicados en repositorio:**

- `backend/django_services/users/serializers.py` → `allow_blank=True` en campos opcionales de `ChatbotAnalysisSerializer`
- `backend/flask-services/src/services/process_data/medical_data.py` → coerción segura de `pain_scale` y `triaje_level="" -> None`
- `backend/flask-services/src/services/api/send_api.py` → uso de `Config.FLASK_API_KEY`
- `backend/flask-services/src/config/config.py` → `FLASK_API_KEY = os.getenv('FLASK_API_KEY', SECRET_KEY)`
- `backend/flask-services/src/services/chatbot/application/turn_persistence_service.py` → evita persistir `triaje_level=""`
- `backend/django_services/users/tests.py` y `backend/flask-services/tests/test_medical_data_processor.py` → regresiones añadidas

**Verificación ejecutada:**

- `python manage.py test users.tests` → OK
- `python -m unittest backend\\flask-services\\tests\\test_medical_data_processor.py` → OK
- `backend\\flask-services\\tests\\test_etl_runner.py` → OK con bootstrap aislado por dependencias locales faltantes (`boto3`, `bson`) fuera del entorno de test directo

---

#### Diagnóstico completo — tres causas raíz independientes

**Causa A (principal) — `allow_blank=True` ausente en `ChatbotAnalysisSerializer`**

Archivo: `django_services/users/serializers.py`

```python
# Estado actual — ROTO
class ChatbotAnalysisSerializer(serializers.Serializer):
    triaje_level   = serializers.CharField(required=False, allow_null=True)  # allow_blank ausente
    medical_context= serializers.CharField(required=False, allow_null=True)  # allow_blank ausente
    allergies      = serializers.CharField(required=False, allow_null=True)  # allow_blank ausente
    medications    = serializers.CharField(required=False, allow_null=True)  # allow_blank ausente
    medical_history= serializers.CharField(required=False, allow_null=True)  # allow_blank ausente
    ocupacion      = serializers.CharField(required=False, allow_null=True)  # allow_blank ausente
```

DRF tiene `allow_blank=False` por defecto en `CharField`. Cualquier campo con `""` produce validación fallida y `{"error": "Datos médicos inválidos", "details": {...}}` con HTTP 400.

Flask envía `""` sistemáticamente en los siguientes casos confirmados en `medical_data.py`:
- `extract_allergies()` → devuelve `""` si no hay alergias detectadas
- `extract_medications()` → devuelve `""` si no hay medicaciones detectadas
- `extract_medical_history()` → devuelve `""` si no hay historial
- `extract_occupation()` → devuelve `""` si no detecta ocupación
- `triaje_level` → `turn_persistence_service.py` línea 62: `response_data.get("triaje_level", "")` inicializa como `""`

Esto significa que **el 400 ocurre en prácticamente todas las conversaciones** que no tienen todos los campos rellenos, es decir, la inmensa mayoría.

**Causa B (secundaria) — `pain_scale` puede llegar como float a un `IntegerField`**

Archivo: `flask-services/.../medical_data.py` → `extract_structured_data()`

```python
"pain_scale": conversation.get("pain_scale"),  # puede ser float, None, o int
```

MongoDB no tiene tipado estricto. Si `pain_scale` se guardó como `7.0` (float), el `IntegerField(min_value=0, max_value=10)` de DRF lanza `ValidationError` (espera int, recibe float). Resultado: otro 400.

**Causa C (terciaria) — Mismatch en el nombre del token de integración**

Archivo Flask: `flask-services/src/services/api/send_api.py`
```python
headers["X-Django-Integration-Token"] = Config.SECRET_KEY   # usa SECRET_KEY de Flask
```

Archivo Django: `django_services/users/views.py`
```python
expected_token = getattr(settings, "FLASK_API_KEY", "") or ""  # busca FLASK_API_KEY
```

Si `FLASK_API_KEY` no está definida en el `.env` de Django (variable diferente a `SECRET_KEY`), `_is_valid_integration_token()` retorna `False`. Si además el `jwt_token` es `None` (caso del timer de inactividad, que llama a `enqueue_etl_run` sin JWT), la vista retorna **401** en lugar de procesar. Este bug provoca pérdida silenciosa de todos los ETL por timeout de inactividad.

---

#### Archivos afectados

- `django_services/users/serializers.py` → `ChatbotAnalysisSerializer` (Causa A)
- `django_services/users/models.py` → `Patient.update_from_chatbot_analysis()` (verificar coerción de tipos)
- `flask-services/src/services/process_data/medical_data.py` → `extract_structured_data()` (Causa B)
- `flask-services/src/services/api/send_api.py` → `_auth_headers()` (Causa C)
- `django_services/config/settings.py` → añadir `FLASK_API_KEY` (Causa C)
- `.env` (Flask y Django) → alinear nombres de variables

---

#### Pasos de implementación

**Fix A — `ChatbotAnalysisSerializer` (2 líneas de cambio, impacto máximo):**

```python
# django_services/users/serializers.py
class ChatbotAnalysisSerializer(serializers.Serializer):
    triaje_level    = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    pain_scale      = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=10)
    medical_context = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    allergies       = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    medications     = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    medical_history = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    ocupacion       = serializers.CharField(required=False, allow_null=True, allow_blank=True)
```

**Fix B — Coerción explícita de `pain_scale` en Flask antes de enviar:**

```python
# flask-services/src/services/process_data/medical_data.py
def extract_structured_data(self, conversation, messages, enhanced_entities):
    raw_pain = conversation.get("pain_scale")
    pain_scale = None
    if raw_pain is not None:
        try:
            pain_scale = int(float(raw_pain))          # convierte 7.0 → 7, "7" → 7
            pain_scale = max(0, min(10, pain_scale))   # clamp 0-10 por seguridad
        except (ValueError, TypeError):
            pain_scale = None                           # valor corrupto → None es aceptado
    return {
        "triaje_level":    conversation.get("triaje_level") or None,  # "" → None
        "pain_scale":      pain_scale,
        "medical_context": "",
        "allergies":       self.extract_allergies(messages, enhanced_entities),
        "medications":     self.extract_medications(enhanced_entities),
        "medical_history": self.extract_medical_history(messages, enhanced_entities),
        "ocupacion":       self.extract_occupation(messages),
    }
```

Nota: `conversation.get("triaje_level") or None` convierte `""` a `None`, que el serializer acepta con `allow_null=True`.

**Fix C — Alinear nombre del token de integración:**

1. En `.env` de Django: añadir `FLASK_API_KEY=<mismo valor que SECRET_KEY de Flask>`
2. En `django_services/config/settings.py`: verificar que se lea `FLASK_API_KEY = env('FLASK_API_KEY', default='')`
3. En `flask-services/src/config/config.py`: añadir `FLASK_API_KEY = os.getenv('FLASK_API_KEY', SECRET_KEY)` para usar variable explícita
4. En `flask-services/src/services/api/send_api.py`: cambiar a usar `Config.FLASK_API_KEY`:

```python
def _auth_headers(jwt_token=None):
    headers = {"Content-Type": "application/json"}
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"
    else:
        headers["X-Django-Integration-Token"] = Config.FLASK_API_KEY  # antes: Config.SECRET_KEY
    return headers
```

5. Verificar que el timer de inactividad pasa `jwt_token` cuando está disponible; si no, la causa C debe estar resuelta para que el token de integración funcione correctamente.

---

#### Verificación post-fix

Ejecutar antes y después del fix:

```bash
# Desde el contenedor Flask o localmente
curl -X POST http://django:8000/api/patients/medical_data_update/ \
  -H "Content-Type: application/json" \
  -H "X-Django-Integration-Token: <FLASK_API_KEY>" \
  -d '{
    "user_id": "<uuid-paciente-test>",
    "medical_data": {
      "triaje_level": "",
      "pain_scale": 0,
      "medical_context": "Test",
      "allergies": "",
      "medications": "",
      "medical_history": "",
      "ocupacion": ""
    },
    "source": "chatbot"
  }'
# Antes del fix → 400 {"error": "Datos médicos inválidos", "details": {...}}
# Después del fix → 200 {"message": "Información del paciente actualizada correctamente"}
```

También ejecutar el test existente: `pytest flask-services/tests/test_etl_runner.py -v`

---

#### Criterio de aceptación

- Una conversación de triaje completa que termine por timeout de inactividad persiste los datos correctamente en PostgreSQL (verificar tabla `users_patienthistoryentry`)
- Una conversación donde el usuario no mencione alergias, medicaciones ni historial (`allergies=""`, `medications=""`) completa la ETL sin errores 400
- Los logs de Flask no muestran `"Error al enviar datos a Django API: 400"` en ninguna conversación de triaje completa

---

**Dependencias:** Ninguna. Ya cerrada; usar esta tarjeta como referencia de implementación y validación de la Fase 0.

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
| `docker-compose.yml` | #5, #12, #17, #21, #39, #40, #41 |
| `worker/etl_consumer.py` | #17, #19, #20 |
| `worker/celery_app.py` + `worker/tasks/chat_tasks.py` | #17, #18 |
| `emergency.yaml` + `emergency_guard.py` | #32 |
| `gateway/main.py` + `gateway/routers/ws_router.py` | #39, #42 |
| `gateway/middleware/auth.py` + `gateway/middleware/rate_limit.py` | #39 |
| `gateway/services/orchestrator.py` | #39, #40, #41, #42 |
| `ai-service/services/bedrock_claude.py` | #40, #42 |
| `ai-service/services/comprehend_medical.py` + `conversation_context.py` | #40 |
| `ai-service/routers/inference.py` | #40, #42 |
| `expert-service/services/expert_orchestrator.py` | #41 |
| `expert-service/services/emergency_guard.py` | #41, #42 |
| `expert-service/routers/triage.py` | #41, #42 |
| `expert-service/rules/` (YAMLs) | #23, #32, #41 |
| `django_services/users/serializers.py` → `ChatbotAnalysisSerializer` | **#43** (Causa A) |
| `flask-services/src/services/process_data/medical_data.py` | #27, **#43** (Causa B) |
| `flask-services/src/services/api/send_api.py` | #1, **#43** (Causa C) |
| `.env` (Django) + `config/settings.py` → `FLASK_API_KEY` | **#43** (Causa C) |
