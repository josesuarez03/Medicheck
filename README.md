# MediCheck — API de Inteligencia para Respuesta a Desastre

API pura de triaje y conversación médica para el **terremoto de Venezuela (24 jun 2026)**.
Expone únicamente el núcleo de IA (gateway + expert-service + ai-service) como HTTP + WebSocket,
consumible por cualquier cliente externo (bot de Telegram/WhatsApp, app móvil, frontend ligero).

**Rama de respaldo con el stack completo (Next.js, Django, MongoDB):** [`main-fullstack`](../../tree/main-fullstack)

## Qué se eliminó del stack original

**Eliminado:** Django, Next.js, MongoDB, Celery, RabbitMQ, Flower.

**Conservado:** `gateway`, `expert-service`, `ai-service` (FastAPI), Postgres (pgvector), Redis.

Principio de cambio: **cirugía mínima, no reescritura.** Se desconectaron las dependencias
muertas preservando la lógica de negocio (lifecycle de conversaciones, cifrado, scoring),
migrando el backend de datos activos a Redis.

## Arquitectura (docker-compose)

| Servicio | URL | Rol |
|---|---|---|
| `gateway` (FastAPI) | `http://localhost:5000` | Entrada HTTP/WebSocket, emite/verifica JWT |
| `ai-service` (FastAPI) | `http://localhost:5001` | Conversación (Claude/Bedrock), RAG, cifrado |
| `expert-service` (FastAPI) | `http://localhost:5002` | Detección de red flags / emergencia |
| `postgres` (pgvector) | `localhost:5432` | Embeddings + catálogo de condiciones |
| `redis` | `localhost:6379` | Conversaciones activas (cifradas) + contexto |
| Observabilidad | — | Prometheus, Grafana, Jaeger, Dozzle, cAdvisor |

## Identidad de usuario (sin Django)

El cliente obtiene un JWT de corta duración:

```
POST /auth/session
Body: {"user_id": "<UUID opcional>"}   # si se omite, el gateway lo genera
Resp: {"access_token": "<JWT>", "user_id": "...", "token_type": "bearer", "expires_in": 86400}
```

Ese token se usa como `Authorization: Bearer <JWT>` en HTTP y en el WebSocket
(`{"type":"auth","token":"<JWT>"}`). Es el **mismo esquema JWT** en ambos canales.

## Seguridad

- **Cifrado en reposo:** `messages` y `medical_context` cifrados con Fernet
  (`CHAT_ENCRYPTION_KEY`) antes de guardarse en Redis.
- **JWT robusto:** sin `JWT_SECRET` el gateway **no arranca** (se eliminó el fallback inseguro).
  Token inválido o ausente → 401.
- **Concurrencia hacia Bedrock:** limitador (`BEDROCK_MAX_CONCURRENCY`) que acota invocaciones
  paralelas para evitar throttling. FastAPI async + workers de uvicorn + aislamiento de estado
  en Redis soportan múltiples chats abiertos simultáneamente.

## Motor semántico (RAG sobre pgvector)

Captura **señales psicológicas** como primera clase (`EMOTIONAL_STATE`, `TRAUMA_EXPOSURE`,
`SUICIDAL_RISK`, `GRIEF`, `SOCIAL_SUPPORT`, `CRISIS_STATE`), de modo que conversaciones de
angustia/duelo/crisis también generan embedding y alimentan el contexto.

### Catálogo de condiciones

`backend/ai-service/scripts/data/conditions.yaml` define ~30 condiciones físicas y psicológicas
(sinónimos coloquiales, señales, urgencia, next_step, country_context). Se cargan en
`rag.conditions_catalog` y se recuperan por similitud por turno para inyectarlas en el prompt.

```bash
cd backend/ai-service
python scripts/seed_conditions.py
```

## Sistema experto

`expert-service` detecta emergencias físicas y psicológicas y escala de inmediato.
La **ideación suicida/autolesión escala siempre** (`emergency_triggered=True`).

Casos nuevos de catástrofe: trauma físico, deshidratación, crisis respiratoria por polvo,
estrés agudo/TEPT, duelo agudo, crisis de pánico, insomnio/pesadillas, ideación suicida,
ansiedad por separación, duelo migratorio (diáspora).

## Contexto dual Venezuela / fuera de Venezuela

Las recomendaciones usan la línea **171** y Protección Civil (0800-558.84.27 / 0800-266.84.46)
para usuarios en Venezuela, y un mensaje genérico para quienes están fuera.
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
`JWT_ALGORITHM`, `REDIS_*`, `POSTGRES_*`.

Recomendadas en producción: `CHAT_ENCRYPTION_KEY` (clave Fernet dedicada),
`INTERNAL_SHARED_SECRET`, credenciales AWS para Bedrock.

## Tests

```bash
cd backend/ai-service
python -m pytest tests/ -v

cd backend/expert-service
python -m pytest tests/ -v
```

## Estructura del proyecto

```text
Medicheck/
├── backend/
│   ├── gateway/          # FastAPI — entrada HTTP/WS, JWT, proxy a ai/expert
│   ├── ai-service/       # FastAPI — conversación, RAG, embeddings, cifrado
│   │   ├── scripts/      # seed_conditions.py + conditions.yaml
│   │   └── tests/
│   └── expert-service/   # FastAPI — sistema experto, reglas YAML/JSON, triaje
│       └── rules/        # casos (10 nuevos) + shared (emergency, triage_policy)
├── docker/
│   ├── postgres/init/    # SQL de esquema y catálogo de condiciones
│   └── observability/    # Prometheus, Grafana, Jaeger
├── docs/superpowers/specs/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Aviso clínico

Este sistema ofrece apoyo de triaje inicial y no sustituye la evaluación clínica profesional.
En emergencias graves, contacta servicios de emergencia locales (Venezuela: 171).

## Licencia

Licencia propietaria — "All rights reserved". Consulta `LICENSE` para condiciones de uso.
