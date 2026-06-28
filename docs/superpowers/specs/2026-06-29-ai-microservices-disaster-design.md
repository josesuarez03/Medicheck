# Design: ai-microservices-disaster

**Fecha:** 2026-06-29  
**Rama:** `ai-microservices-disaster` (creada desde `origin/feature`)  
**Contexto:** Respuesta a terremoto Venezuela 24-jun-2026. Se elimina el stack completo (Django, Next.js, MongoDB, Celery/RabbitMQ) y se expone solo el núcleo de inteligencia (gateway + expert-service + ai-service) como API pura HTTP/WebSocket.

---

## Principio rector

**Cirugía mínima, no reescritura.** Cada cambio preserva la lógica de negocio existente y solo desconecta el backend de datos que ya no existe. Un diff contra `feature` debe ser legible y autoexplicativo.

---

## Sección 1 — Cirugía quirúrgica (desconexión Mongo/Django)

### 1.1 `backend/ai-service/models/conversation.py`

`ConversationalDatasetManager.__init__` actualmente falla al instanciar `mongo_db['conversations']` con `mongo_db = None`.

**Fix:** En `__init__`, en vez de acceder a `mongo_db['conversations']`, inicializar `self._cache = RedisCacheManager()` dentro de un `try/except`. Los métodos públicos delegan a `self._cache`:

| Método público | Delegado a |
|---|---|
| `get_conversations(user_id, view)` | `self._cache.obtener_todas_conversaciones(user_id)` + filtro Python por `lifecycle_status` |
| `get_conversation(user_id, conv_id)` | `self._cache.obtener_conversacion(user_id, conv_id)` |
| `add_conversation(user_id, data)` | `self._cache.guardar_conversacion(user_id, data)` |
| `archive_conversation(...)` | `self._cache.archivar_conversacion(...)` |
| `recover_conversation(...)` | `self._cache.recuperar_conversacion(...)` |
| `soft_delete_conversation(...)` | `self._cache.eliminar_conversacion(...)` |
| `soft_delete_all_conversations(...)` | iterar índice Redis, eliminar cada una |

El filtrado por `view` (`active`/`archived`/`all`) que Mongo hacía con `$or` se resuelve en Python sobre la lista devuelta por Redis — volumen por usuario es bajo (TTL 24h).

`RedisCacheManager` no se modifica en su lógica interna.

### 1.2 `backend/ai-service/routers/inference.py` línea 42

`conversation_manager = ConversationalDatasetManager()` se instancia al importar. Si 1.1 se resuelve bien, deja de romper. Verificar con import real (con env vars seteadas) antes de dar por cerrado.

### 1.3 `backend/ai-service/services/conversation_context_service.py`

Ya tiene `try/except` defensivo en el import de `data/connect.py`. Ahora que ese módulo existe, el import debe funcionar. `get_global_patient_context_mongo()` ya devuelve `{"recent_conversations": []}` cuando `mongo_db = None` — no requiere cambios. Verificar con prueba real.

### 1.4 `backend/ai-service/services/django_summary_client.py`

`DjangoClinicalSummaryClient.enabled` accede a `Config.DJANGO_API_URL_FLASK` que ya no existe → `AttributeError`.

**Fix (1 línea):** Reemplazar acceso directo por `getattr(Config, "DJANGO_API_URL_FLASK", None)` y `getattr(Config, "DJANGO_API_URL", None)`. `enabled` devuelve `False` de forma segura. El archivo se mantiene completo para eventual reconexión futura.

### 1.5 `backend/gateway/services/orchestrator.py`

Bloque que llama a `enqueue_etl_dispatch`/`schedule_inactivity_etl`/`clear_inactivity_token` depende de Celery/RabbitMQ eliminados.

**Fix:** Comentar el bloque condicional (`ai_conversation_state.get("should_trigger_etl")` / `"awaiting_closure_confirmation"`), forzar `etl_dispatch = None` siempre. Comentario explica que el pipeline ETL→Django/Mongo no aplica en esta rama.

### 1.6 `backend/gateway/services/etl_dispatcher.py`

Solo intervenir si el import de Celery/RabbitMQ falla al cargar el módulo (sin llamarlo). Si es el caso: envolver imports en `try/except`, devolviendo funciones no-op. No borrar el archivo.

---

## Sección 2 — Seguridad

### 2.1 Cifrado en Redis

**Problema:** `RedisCacheManager.guardar_conversacion()` guarda JSON en claro. Con Redis como único almacenamiento de conversaciones activas, esto expone contenido clínico/psicológico sensible.

**Fix:**
- `Config`: renombrar `MONGO_ENCRYPTION_KEY` → `CHAT_ENCRYPTION_KEY`. Backward compat: si `CHAT_ENCRYPTION_KEY` no está seteada, usar `MONGO_ENCRYPTION_KEY` como fallback, y si tampoco existe, derivar de `SECRET_KEY` con SHA256+base64 (igual que el esquema actual).
- `RedisCacheManager.guardar_conversacion()`: cifrar campos `messages` y `medical_context` con `Encryption` antes de serializar a JSON.
- `RedisCacheManager.obtener_conversacion()`: descifrar al leer.
- Verificar con prueba: cifrar payload → guardar en Redis → leer → descifrar → contenido idéntico al original.

### 2.2 JWT — Fix vulnerabilidad de fallback inseguro

**Vulnerabilidad actual:** `decode_access_token` en `backend/gateway/middleware/auth.py` devuelve `{"raw_token": token}` cuando `jwt is None` o `JWT_SECRET` está vacío — acepta cualquier string como token válido.

**Fix:**
```python
if jwt is None or not JWT_SECRET:
    raise HTTPException(status_code=401, detail="Servicio de autenticación no disponible.")
```

### 2.3 JWT — Emisión en gateway (reemplaza Django)

Nuevo endpoint `POST /auth/session` en gateway:
- Body: `{"user_id": "<UUID opcional>"}` — si el cliente no lo provee, el gateway genera uno.
- Respuesta: `{"access_token": "<JWT>", "user_id": "<UUID>", "expires_in": 86400}`
- El JWT contiene `sub=user_id`, `iat`, `exp` (24h). Firmado con `JWT_SECRET` y `JWT_ALGORITHM`.
- Usa `python-jose` que ya está en el proyecto — no se introduce ninguna librería nueva.

### 2.4 Configuración obligatoria de JWT_SECRET

`Config.validate()` en gateway: `JWT_SECRET` o `SECRET_KEY` son obligatorios. El servicio no arranca si faltan. Mismo patrón de `validate()` que ya usa `ai-service/config/config.py`.

---

## Sección 3 — Docker cleanup

### Servicios eliminados del `docker-compose.yml`

| Servicio | Razón |
|---|---|
| `django-api-principal` | Django eliminado |
| `mongo` | MongoDB eliminado |
| `rabbitmq` | Broker Celery eliminado |
| `celery-worker-chat` | Worker eliminado |
| `celery-worker-etl` | Worker eliminado |
| `flower` | Monitor Celery eliminado |
| `frontend` | Next.js eliminado |
| `rabbitmq-exporter` | Sin RabbitMQ |
| `mongodb-exporter` | Sin MongoDB |

**Volúmenes eliminados:** `mongo_data`, `rabbitmq_data`

### `depends_on` actualizados

- `gateway`: solo depende de `redis`, `postgres`, `ai-service`, `expert-service`
- `ai-service`: solo depende de `postgres`, `redis`
- `prometheus`: eliminar `rabbitmq-exporter` y `mongodb-exporter` de su `depends_on`

### Servicios mantenidos

`postgres`, `redis`, `gateway`, `ai-service`, `expert-service`, `dozzle`, `cadvisor`, `postgres-exporter`, `redis-exporter`, `blackbox-exporter`, `prometheus`, `grafana`, `jaeger`

---

## Sección 4 — Motor semántico: señales psicológicas

### 4.1 `backend/ai-service/services/medical_facts.py`

**Nuevas categorías en `FactCategory`:**
```python
"EMOTIONAL_STATE"   # angustia, miedo, desesperación
"TRAUMA_EXPOSURE"   # exposición directa al desastre, pérdidas vivenciadas
"SUICIDAL_RISK"     # ideación suicida o autolesión — señal de máxima prioridad
"GRIEF"             # duelo por pérdida de personas o bienes
"SOCIAL_SUPPORT"    # aislamiento, falta de red de apoyo
"CRISIS_STATE"      # estado de crisis aguda, desbordamiento emocional
```

**Nuevos campos en `FactsSummary`:**
```python
psych_signals: list[str] = []
trauma_indicators: list[str] = []
suicidal_risk: list[str] = []
```

### 4.2 `backend/ai-service/services/embeddings.py`

- `should_embed()`: añadir `{"EMOTIONAL_STATE", "TRAUMA_EXPOSURE", "SUICIDAL_RISK", "GRIEF", "CRISIS_STATE"}` al trigger set junto a `SYMPTOM`, `MEDICATION`, etc.
- `_ordered_fields()`: incluir `psych_signals`, `trauma_indicators`, `suicidal_risk` de `FactsSummary` en el texto serializado para embeddings.

### 4.3 `backend/ai-service/services/comprehend_medical.py`

AWS Comprehend Medical no cubre señales emocionales en español de forma fiable. Se añaden heurísticas rule-based en paralelo:
- Diccionario de señales psicológicas en español (incluyendo coloquialismos venezolanos)
- Regex para frases de riesgo (`no quiero vivir`, `mejor muerto`, `no aguanto más`, etc.) → mapean a `SUICIDAL_RISK`
- Frases de duelo/pérdida → `GRIEF`
- Frases de crisis aguda → `CRISIS_STATE`

Validación: mensajes de prueba en español (solo emocional, sin síntomas físicos) deben generar embedding via `should_embed() = True`.

---

## Sección 5 — Sistema experto: nuevos casos

Solo formato `.yaml` para los casos nuevos (no duplicar en `.json`).

### Casos físicos (catástrofe/terremoto)

| `case_id` | Alcance |
|---|---|
| `trauma_fisico` | heridas, fracturas, aplastamiento, sangrado, atrapamiento bajo escombros |
| `deshidratacion` | deshidratación, intoxicación por agua/alimentos contaminados |
| `respiratorio_polvo` | inhalación de polvo de escombros, crisis asmática, dificultad respiratoria |

### Casos psicológicos/salud mental

| `case_id` | Alcance |
|---|---|
| `estres_agudo_ptsd` | estrés agudo / PTSD post-terremoto, flashbacks, hipervigilancia |
| `duelo_agudo` | pérdida de familiares, duelo agudo, shock emocional |
| `crisis_panico` | ataques de pánico, taquicardia sin causa física, terror repentino |
| `insomnio_pesadillas` | insomnio post-trauma, pesadillas recurrentes sobre el sismo |
| `ideacion_suicida` | **SIEMPRE dispara `emergency_triggered = True`** — no hay nivel "leve" para esto |
| `ansiedad_separacion` | incertidumbre por familiares desaparecidos, sin poder contactarlos |
| `duelo_migratorio` | duelo desde el exterior, impotencia por distancia, diáspora venezolana |

### Reglas transversales

- `intent_keywords` incluyen variantes coloquiales venezolanas (no solo lenguaje clínico)
- Mensajes `advice` en nivel Severo/Emergencia recomiendan explícitamente buscar psicólogo/profesional
- Cuando `country_context != "VE"` (o se infiere): los `advice` usan texto genérico ("contacta servicios de emergencia de tu país") en vez de 171/Protección Civil

---

## Sección 6 — Catálogo de condiciones en pgvector

### Schema SQL (nueva migración)

```sql
CREATE TABLE conditions_catalog (
    id               SERIAL PRIMARY KEY,
    condition_id     VARCHAR(100) UNIQUE NOT NULL,
    name             VARCHAR(200) NOT NULL,
    synonyms         JSONB DEFAULT '[]',
    signals          JSONB DEFAULT '[]',
    urgency_level    VARCHAR(20)  CHECK (urgency_level IN ('low','moderate','high','emergency')),
    next_step        VARCHAR(50)  CHECK (next_step IN ('self_care','doctor','psychologist','emergency')),
    country_context  VARCHAR(10)  DEFAULT 'ALL',
    source           VARCHAR(200),
    embedding        vector(1536),
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX conditions_catalog_embedding_idx
    ON conditions_catalog USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);
```

### Contenido del catálogo (~35 condiciones)

- **Físicas catástrofe:** trauma físico, fracturas, heridas abiertas, aplastamiento, hemorragia, deshidratación, intoxicación alimentaria, crisis asmática/respiratoria, quemaduras leves/moderadas
- **Psicológicas:** estrés agudo post-desastre, PTSD, duelo agudo, crisis de pánico, insomnio post-trauma, ideación suicida, ansiedad por separación, duelo migratorio, depresión reactiva
- **Crónicas comunes** que pueden descompensarse en el contexto del desastre: hipertensión, diabetes, asma, epilepsia

Cada condición incluye: `synonyms` (cómo la gente la describe coloquialmente), `signals` (señales típicas), `urgency_level`, `next_step`, `country_context` (para condiciones con referencias VE-específicas).

### Script de carga

`scripts/seed_conditions.py`:
1. Lee un archivo fuente `scripts/data/conditions.yaml` con las ~35 condiciones
2. Genera embeddings via Bedrock (con fallback hash-based de `embeddings.py` si Bedrock no disponible)
3. Inserta/actualiza en `conditions_catalog` via upsert on `condition_id`
4. Loguea cuántas se insertaron/actualizaron

### Flujo de recuperación por turno

1. `bedrock_claude.py` recibe el mensaje del usuario + el embedding de la consulta
2. Llama `vector_store.get_relevant_conditions(query_embedding, top_k=3, country=user_country)`
3. Las 3 condiciones más relevantes se inyectan en `build_turn_prompt()` como bloque `<conditions_context>` antes del mensaje del usuario
4. El filtro `country_context` asegura que condiciones con números venezolanos no aparezcan para usuarios fuera de VE

---

## Validaciones requeridas antes de cerrar cada punto

| Punto | Validación |
|---|---|
| Cirugía Mongo | `import backend/ai-service/routers/inference.py` con env vars reales → sin errores |
| Cirugía Django summary | `DjangoClinicalSummaryClient().enabled` → `False`, sin AttributeError |
| Cifrado Redis | cifrar payload → guardar → leer → descifrar → contenido idéntico |
| JWT inseguro | token inválido sin JWT_SECRET → HTTP 401, no 200 |
| JWT emisión | `POST /auth/session` → JWT válido verificable con `decode_access_token` |
| Señales psicológicas | mensaje emocional puro (sin síntomas físicos) → `should_embed() = True` |
| Sistema experto | `ExpertOrchestrator().evaluate("me quiero morir")` → `emergency_triggered = True` |
| pgvector catálogo | `seed_conditions.py` → inserción OK → `get_relevant_conditions("dolor de cabeza")` → top-3 coherentes |

---

## Lo que NO se hace en esta rama

- No se reintroduce Django, Next.js, MongoDB, Celery ni RabbitMQ
- No se reescriben archivos completos cuando un fix de 1-3 líneas resuelve el problema
- No se elimina lógica de lifecycle/cifrado/scoring solo porque estaba asociada a Mongo
- No se quita al expert-service su capacidad de detectar emergencias físicas existentes
