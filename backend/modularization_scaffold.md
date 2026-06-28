# Modularizacion inicial del servicio Flask

Este arbol crea una base nueva para la arquitectura objetivo del plan sin tocar `backend/flask-services`.

Servicios creados:

- `backend/gateway`: bootstrap FastAPI para gateway HTTP/WS.
- `backend/ai-service`: bootstrap FastAPI para inferencia.
- `backend/expert-service`: bootstrap FastAPI para sistema experto.
- `backend/worker`: base de worker ETL.

Codigo copiado del monolito:

- Modulos de IA desde `backend/flask-services/src/services/chatbot/`.
- Modulos ETL desde `backend/flask-services/src/services/process_data/`.
- Integracion Django desde `backend/flask-services/src/services/api/send_api.py`.
- Acceso a Mongo/Redis y modelos conversacionales reutilizados para referencia de migracion.
- Reglas YAML y `emergency_guard.py` del sistema experto.

Estructura alineada con el plan:

- `gateway/requirements.txt`, `ai-service/requirements.txt`, `expert-service/requirements.txt`, `worker/requirements.txt`
- `ai-service/services/bedrock_claude.py`
- `ai-service/services/comprehend_medical.py`
- `ai-service/services/conversation_context.py`
- `ai-service/services/embeddings.py`
- `expert-service/services/expert_orchestrator.py`
- `expert-service/services/emergency_guard.py`
- `expert-service/services/triage_classification.py`
- `worker/etl_consumer.py` con soporte ETL en `worker/services/*.py`

Alcance intencional:

- El Flask actual permanece intacto y sigue siendo la referencia operativa.
- Los scripts FastAPI creados son bootstrap de arquitectura, no reemplazo funcional completo.
- Cada servicio contiene solo la base alineada con su responsabilidad actual.
- El `worker` se ha dejado limitado a ETL; la migracion del worker de chat se difiere hasta extraer esa funcionalidad de forma aislada.
