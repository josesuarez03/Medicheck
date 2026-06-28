# Auditoría de Estado Real Tras Migración a FastAPI

Fecha: 2026-03-30

Documento auditado:
- `docs/plans/mejoras/2026-03-20_plan_mejoras_hipo_v3_skills.md`

Objetivo:
- verificar qué tareas del plan están realmente cerradas en el repositorio actual
- separar lo que está cerrado en código de lo que está cerrado operativamente
- detectar tareas que han quedado obsoletas o reabiertas por la migración Flask -> FastAPI

## Resumen ejecutivo

Conclusión principal:
- la migración a FastAPI existe en código, pero no está cerrada operativamente

Hallazgos críticos:
- el repositorio ya no contiene `backend/flask-services`, pero `docker-compose.yml` sigue levantando `flask-api-chat` desde `flask-services/Dockerfile` y deja `gateway`, `ai-service` y `expert-service` comentados
- el frontend sigue usando `socket.io-client`, eventos `authenticate` y `chat_message`, mientras el nuevo gateway expone un WebSocket nativo en `/ws` con contrato JSON distinto
- varias mejoras que estaban cerradas en Flask quedan reabiertas en la arquitectura nueva porque el gateway FastAPI todavía no replica ese hardening

Estado global recomendado:
- cerradas de verdad: 15
- cerradas en código pero no operativas: 7
- parciales / muy avanzadas: 9
- abiertas: 10
- obsoletas por migración: 4

## Evidencia clave

- `docker-compose.yml` sigue apuntando al stack viejo en [docker-compose.yml](/c:/Users/josys/Documents/TFG/docker-compose.yml#L31) y deja el stack nuevo comentado en [docker-compose.yml](/c:/Users/josys/Documents/TFG/docker-compose.yml#L293)
- `README.md` sigue documentando Flask y `backend/flask-services` en [README.md](/c:/Users/josys/Documents/TFG/README.md#L8), [README.md](/c:/Users/josys/Documents/TFG/README.md#L123) y [README.md](/c:/Users/josys/Documents/TFG/README.md#L166)
- el nuevo gateway existe en [backend/gateway/main.py](/c:/Users/josys/Documents/TFG/backend/gateway/main.py#L1) y [backend/gateway/routers/http_router.py](/c:/Users/josys/Documents/TFG/backend/gateway/routers/http_router.py#L1)
- el WebSocket nuevo no usa JWT real, ni Redis para sesión, ni rate limit WS en [backend/gateway/routers/ws_router.py](/c:/Users/josys/Documents/TFG/backend/gateway/routers/ws_router.py#L11)
- el frontend sigue acoplado a Socket.IO en [frontend/src/services/ws.ts](/c:/Users/josys/Documents/TFG/frontend/src/services/ws.ts#L1)
- la seguridad interna HMAC sí está implementada entre worker/Django y Django/ai-service en [backend/worker/services/send_api.py](/c:/Users/josys/Documents/TFG/backend/worker/services/send_api.py#L41), [backend/django_services/users/views.py](/c:/Users/josys/Documents/TFG/backend/django_services/users/views.py#L328) y [backend/ai-service/routers/inference.py](/c:/Users/josys/Documents/TFG/backend/ai-service/routers/inference.py#L40)

## Reclasificación por tarea

| # | Estado real | Dictamen |
|---|-------------|----------|
| 1 | Cerrada real | HMAC y timestamp activos entre worker -> Django; también se firma sync hacia ai-service. |
| 2 | Cerrada real | `AuditLog` y utilidades de firma presentes. |
| 3 | Cerrada real | Campos clínicos cifrados con `EncryptedTextField` y claves obligatorias en settings. |
| 4 | Cerrada real | El cifrado Mongo de conversaciones vive ahora en `ai-service/models/conversation.py`. |
| 5 | Parcial | Redis con contraseña sí; TLS solo configurable en Django y no operativo en el stack Docker actual. |
| 6 | Cerrada real | Endpoints sensibles con JWT y tokens firmados siguen presentes en Django. |
| 7 | Obsoleta por migración | La clase `Encryption` de Flask ya no aplica; la sustituta existe en `ai-service`. |
| 8 | Cerrada real | No he encontrado evidencia de reapertura; se mantiene el hardening Django previo. |
| 9 | Reabierta | El nuevo WS FastAPI no aplica rate limiting por usuario. |
| 10 | Reabierta | El gateway nuevo guarda `authenticated_user_id` en memoria del socket, no en Redis. |
| 11 | Cerrada real | Hay validación obligatoria de claves críticas en Django y ai-service. |
| 12 | Cerrada real | Hay `/health` en Django, gateway, ai-service y expert-service. |
| 13 | Cerrada real | Throttling en autenticación Django sigue presente. |
| 14 | Parcial | El cierre/ETL se ha rediseñado con `conversation_state`, pero falta validación E2E en la ruta nueva. |
| 15 | Abierta | Sigue habiendo riesgo N+1; `PatientSerializer.get_history_count()` usa `obj.history_entries.count()`. |
| 16 | Cerrada real | Configuración JWT endurecida sigue en Django. |
| 17 | Cerrada real | RabbitMQ, workers separados y Flower activos en compose; tests worker OK. |
| 18 | Obsoleta por migración | La idea de Flask como gateway ligero ha sido sustituida por `gateway` FastAPI. |
| 19 | Cerrada en código, no operativa | Existe `/conversation/etl/retry` en gateway, pero el servicio no está activo en compose. |
| 20 | Abierta | No he encontrado caché Redis de resultados ETL. |
| 21 | Cerrada real | Segmentación Redis por función implementada en compose y config de worker. |
| 22 | Cerrada en código, no operativa | CSP está en `nginx.conf`, pero `nginx` está comentado en compose. |
| 23 | Parcial | `expert-service/rules/cases` ya separa conocimiento clínico, pero no está validado como ampliación suficiente. |
| 24 | Reabierta | El contrato nuevo no usa token en primer mensaje; además frontend y gateway no hablan el mismo protocolo. |
| 25 | Abierta | No hay evento `triage_escalation` en gateway ni frontend. |
| 26 | Parcial | El backend devuelve `response_source`, pero el frontend no lo muestra de forma visible. |
| 27 | Cerrada real | `ai-service` usa prompt compacto con presupuesto; además hay tests de prompt budget. |
| 28 | Abierta | No he encontrado mocks AWS específicos como estrategia consolidada de tests unitarios. |
| 29 | Parcial | La base técnica existe: `PatientClinicalSummary`, embeddings y retrieval; no está cerrada operativamente. |
| 30 | Abierta | No hay detector explícito de contradicciones intra-conversación. |
| 31 | Parcial | `ai-service` ya formula pregunta de cierre y dispara ETL por confirmación. |
| 32 | Parcial | Hay red flags y guard experto, pero no veo implementación completa del eje temporal + intensidad. |
| 33 | Abierta | No hay modo “segunda opinión” en backend ni frontend. |
| 34 | Abierta | `expert-service` calcula `confidence`, pero no se muestra al usuario final. |
| 35 | Reabierta | Hay scheduling de inactividad, pero no timeout visible ni warning de sesión en frontend/gateway nuevo. |
| 36 | Abierta | No he encontrado detección de idioma ni respuesta multilingüe real. |
| 37 | Cerrada en código, no operativa | El backend devuelve `final_chat_summary` y el frontend sabe renderizarlo, pero depende del canal Socket.IO viejo. |
| 38 | Abierta | No he encontrado caché de sistema experto para casos idénticos. |
| 39 | Cerrada en código, no operativa | `gateway` FastAPI existe, pero no está levantado en compose y no sustituye todavía al frontend actual. |
| 40 | Muy avanzada | `ai-service` existe y cubre chat, embeddings, retrieval y consulta libre; falta cierre operativo y dependencias. |
| 41 | Cerrada en código, no operativa | `expert-service` existe con rutas y reglas, pero tampoco está activo en compose. |
| 42 | Parcial | Hay `consult` en ai-service y `emergency-check` en expert-service, pero falta el modo de sesión completo en gateway/frontend. |
| 43 | Cerrada real | La coerción ETL y la firma interna sobreviven en `worker`; tests worker OK. |
| 44 | Parcial | Hay piezas de guardas y resumen clínico, pero el flujo paciente no está estabilizado de extremo a extremo en la arquitectura nueva. |
| 45 | Muy avanzada | El modelo clínico, backfill y RAG existen; falta validación operativa, migraciones y despliegue limpio. |

## Tareas que deben cambiar de estado en el plan

Cambiar a `reabierta`:
- `#9`
- `#10`
- `#24`
- `#35`

Cambiar a `cerrada en código / pendiente activación`:
- `#19`
- `#22`
- `#37`
- `#39`
- `#41`

Mantener como `muy avanzada` o `parcial`:
- `#14`
- `#23`
- `#29`
- `#31`
- `#32`
- `#40`
- `#42`
- `#44`
- `#45`

Cambiar a `obsoleta por migración`:
- `#7`
- `#18`

## Riesgos prioritarios detectados

1. La migración no es arrancable como stack principal.
   - `docker-compose.yml` todavía depende de `flask-services`, que ya no existe.

2. El frontend no es compatible con el nuevo gateway.
   - usa Socket.IO y eventos heredados; el gateway nuevo espera WebSocket nativo y otro payload.

3. Se han perdido garantías de seguridad y sesión al pasar al nuevo gateway.
   - no hay JWT WS real
   - no hay rate limiting WS
   - no hay persistencia de sesión WS en Redis

4. `ai-service` no está validado del todo.
   - sus tests no llegan a ejecutarse completos por faltar `psycopg` en el entorno actual.

## Verificación realizada

Pruebas ejecutadas:
- `python -m pytest backend\\gateway\\tests\\test_orchestrator.py -q` -> `1 passed`
- `python -m pytest backend\\worker\\tests\\test_etl_runner.py -q` -> `5 passed`
- `python -m pytest backend\\ai-service\\tests -q` -> error de colección por dependencia ausente: `ModuleNotFoundError: No module named 'psycopg'`

## Recomendación operativa inmediata

Orden recomendado para cerrar la migración de verdad:

1. Activar `gateway`, `ai-service` y `expert-service` en `docker-compose.yml` y eliminar referencias restantes a `flask-services`.
2. Adaptar `frontend/src/services/ws.ts` y `frontend/src/components/Chatbot.tsx` al contrato del nuevo WebSocket FastAPI.
3. Reimplantar en el gateway nuevo las tareas `#9`, `#10`, `#24` y `#35`.
4. Resolver dependencias y ejecutar la batería de tests de `ai-service`.
5. Solo después actualizar el plan principal marcando como cerradas las tareas afectadas por la migración.
