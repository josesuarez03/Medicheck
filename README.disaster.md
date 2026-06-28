# MediCheck — rama `ai-microservices-disaster`

API pura de inteligencia para respuesta al **terremoto de Venezuela (24 jun 2026)**.
Bifurcación de alcance reducido a partir de `feature`: se conserva solo el núcleo
de triaje y conversación, expuesto como HTTP + WebSocket para que cualquier
cliente externo (otra app, bot de Telegram/WhatsApp, frontend ligero) lo consuma.

## Qué cambia respecto a `feature`

**Eliminado:** `django_services` (Django/auth), `worker` (Celery/RabbitMQ/ETL),
`frontend` (Next.js), MongoDB.

**Conservado:** `gateway`, `expert-service`, `ai-service` (FastAPI), Postgres
(pgvector), Redis.

Principio de cambio: **cirugía mínima, no reescritura.** Se desconectaron las
dependencias muertas (Mongo/Django/Celery) preservando la lógica de negocio
(lifecycle de conversaciones, cifrado, scoring), migrando el backend a Redis.

## Arquitectura (docker-compose)

- `gateway` (FastAPI) → `http://localhost:5000` — entrada HTTP/WebSocket, emite/verifica JWT
- `ai-service` (FastAPI) → `http://localhost:5001` — conversación (Claude/Bedrock), RAG, cifrado
- `expert-service` (FastAPI) → `http://localhost:5002` — detección rápida de red flags / emergencia
- `postgres` (pgvector) → `localhost:5432` — embeddings + catálogo de condiciones
- `redis` → `localhost:6379` — conversaciones activas (cifradas) + contexto
- Observabilidad: prometheus, grafana, jaeger, dozzle, cadvisor, exporters de postgres/redis

## Identidad de usuario (sin Django)

Modelo simple sin contraseña. El cliente obtiene un JWT de corta duración:

```
POST /auth/session
Body: {"user_id": "<UUID opcional>"}   # si se omite, el gateway lo genera
Resp: {"access_token": "<JWT>", "user_id": "...", "token_type": "bearer", "expires_in": 86400}
```

Ese token se usa como `Authorization: Bearer <JWT>` en HTTP y en el WebSocket
(mensaje `{"type":"auth","token":"<JWT>"}`). **Es el mismo esquema JWT** en
ambos canales (`JWT_SECRET_KEY` / `JWT_ALGORITHM`).

## Seguridad

- **Cifrado en reposo:** `messages` y `medical_context` se cifran con Fernet
  (`CHAT_ENCRYPTION_KEY`) antes de guardarse en Redis. En producción, define una
  clave Fernet generada aparte (ver `.env.example`), no la derivada de `SECRET_KEY`.
- **JWT robusto:** sin `JWT_SECRET` el gateway **no arranca** (no hay modo
  inseguro). Un token inválido o ausente devuelve 401 (se eliminó el fallback
  que aceptaba cualquier string).
- **Concurrencia hacia Bedrock:** limitador (`BEDROCK_MAX_CONCURRENCY`) que acota
  invocaciones paralelas a Claude para evitar throttling y controlar costos ante
  picos de chats simultáneos. No se usa un broker de mensajería: FastAPI async +
  workers de uvicorn + aislamiento de estado en Redis ya soportan múltiples
  chats abiertos a la vez.

## Motor semántico (RAG sobre pgvector)

Además de las señales clínicas, el motor captura **señales psicológicas** como
primera clase (`EMOTIONAL_STATE`, `TRAUMA_EXPOSURE`, `SUICIDAL_RISK`, `GRIEF`,
`SOCIAL_SUPPORT`, `CRISIS_STATE`), de modo que una conversación puramente de
angustia/duelo/crisis también genera embedding y alimenta el contexto.

### Catálogo de condiciones

`backend/ai-service/scripts/data/conditions.yaml` define ~30 condiciones físicas
y psicológicas (con sinónimos coloquiales, señales, urgencia, next_step,
country_context). Se cargan en `rag.conditions_catalog` y se recuperan por
similitud por turno e inyectan en el prompt de Claude.

Cargar el catálogo (requiere Postgres y, para embeddings reales, Bedrock):

```bash
cd backend/ai-service
python scripts/seed_conditions.py
```

## Sistema experto

`expert-service` detecta emergencias (físicas y psicológicas) y escala de
inmediato. La **ideación suicida/autolesión escala siempre**
(`emergency_triggered=True`). Casos nuevos de catástrofe: trauma físico,
deshidratación, crisis respiratoria por polvo, estrés agudo/TEPT, duelo agudo,
crisis de pánico, insomnio/pesadillas, ideación suicida, ansiedad por
separación, duelo migratorio (diáspora).

## Enfoque dual Venezuela / fuera de Venezuela

Las recomendaciones de emergencia usan la línea **171** y Protección Civil
(0800-558.84.27 / 0800-266.84.46) para usuarios en Venezuela, y un mensaje
genérico ("servicios de emergencia de tu país") para quienes están fuera.
`DEFAULT_USER_COUNTRY` (default `VE`) es el respaldo cuando no se conoce el país.

## Puesta en marcha

```bash
cp .env.example .env   # completa secretos
docker compose up -d postgres redis expert-service ai-service gateway
# (opcional) cargar el catálogo de condiciones:
docker compose exec ai-service python scripts/seed_conditions.py
```

## Variables de entorno

Ver `.env.example`. Obligatorias para arrancar: `SECRET_KEY`/`JWT_SECRET_KEY`,
`JWT_ALGORITHM`, `REDIS_*`, `POSTGRES_*`. Recomendadas en producción:
`CHAT_ENCRYPTION_KEY` (clave Fernet dedicada), `INTERNAL_SHARED_SECRET`.
