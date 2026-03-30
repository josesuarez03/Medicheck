# MediCheck - Sistema Inteligente de Triaje Medico

Aplicacion web de triaje medico orientada a entornos laborales y educativos, desarrollada como TFG.

Integra:
- Frontend en Next.js (pacientes y doctores)
- API principal en Django REST (usuarios, autenticacion y datos clinicos)
- Microservicio de chat en Flask + Socket.IO (triaje conversacional)
- PostgreSQL, MongoDB y Redis
- Nginx + Certbot para despliegue

## Caracteristicas principales

- Registro/inicio de sesion con JWT y Google OAuth
- Perfiles diferenciados de paciente y doctor
- Chat de triaje en tiempo real (HTTP + WebSocket)
- Clasificacion de triaje y recomendaciones iniciales
- Historial y actualizacion de datos medicos del paciente
- Gestion de conversaciones (activar, archivar, eliminar)

## Arquitectura

Servicios definidos en `docker-compose.yml`:

- `frontend` (Next.js) -> `http://localhost:3000`
- `django-api-principal` (Django REST) -> `http://localhost:8000`
- `flask-api-chat` (Flask + Socket.IO) -> `http://localhost:5000`
- `postgres` (PostgreSQL) -> `localhost:5432`
- `mongo` (MongoDB) -> `localhost:27017`
- `redis` -> `localhost:6379`
- `nginx` (reverse proxy) -> `http://localhost`

## Stack tecnologico

- Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS
- Backend API: Django 5, Django REST Framework, SimpleJWT
- Chatbot: Flask 3, Flask-SocketIO, PyYAML, FAISS, NLTK
- Datos: PostgreSQL, MongoDB, Redis
- Infra: Docker Compose, Nginx, Certbot

## Requisitos

- Docker y Docker Compose
- (Opcional para desarrollo local) Node.js 20+, npm, Python 3.13+

## Puesta en marcha rapida (Docker)

1. Clonar el repositorio.
2. Crear y completar el archivo `.env` en la raiz del proyecto.
3. Construir y levantar servicios:

```bash
docker compose up --build
```

4. Abrir:
- Frontend: `http://localhost:3000`
- API Django: `http://localhost:8000`
- API Chat Flask: `http://localhost:5000/chat`

Para detener:

```bash
docker compose down
```

## Variables de entorno (minimas)

Define estas variables en `.env` (sin subir secretos a GitHub):

### Django / comun

- `DJANGO_SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `JWT_ALGORITHM`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_DB1`

### Flask / chatbot

- `SECRET_KEY` (debe ser coherente con Django)
- `MONGO_INITDB_ROOT_USERNAME`
- `MONGO_INITDB_ROOT_PASSWORD`
- `MONGO_INITDB_DATABASE`
- `MONGO_HOST`
- `MONGO_PORT`
- `REDIS_DB`
- `DJANGO_API_URL`
- `AWS_REGION`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `BEDROCK_EMBEDDING_MODEL_ID` (opcional segun modo)
- `BEDROCK_CLAUDE_MODEL_ID` (opcional segun modo)
- `BEDROCK_CLAUDE_INFERENCE_PROFILE_ID` (opcional segun modo)

### Frontend

- `NEXT_PUBLIC_API_URL` (ej. `http://localhost:8000/`)
- `NEXT_PUBLIC_CHAT_API_URL` (ej. `http://localhost:5000/chat/`)
- `NEXT_PUBLIC_SOCKETIO_URL` (ej. `http://localhost:5000`)
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID`

## Desarrollo local (sin Docker)

### 1) Django API

```bash
cd backend/django_services
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### 2) Flask chat

```bash
cd backend/flask-services
pip install -r requirements.txt
python src/app.py
```

### 3) Frontend

```bash
cd frontend
npm install
npm run dev
```

## Endpoints principales

### Django

- `POST /login/`
- `POST /register/`
- `POST /google/login/`
- `GET/PUT /profile/`
- `POST /password/change/`
- `POST /api/patients/medical_data_update/`

### Flask chat

- `POST /chat/message`
- `GET /chat/conversations`
- `GET /chat/conversation/<conversation_id>`
- `POST /chat/conversation/<conversation_id>/archive`
- `POST /chat/conversation/<conversation_id>/recover`
- `DELETE /chat/conversation/<conversation_id>`
- `POST /chat/process_medical_data`

Eventos Socket.IO:
- `chat_message`
- `chat_response`

## Tests

Pruebas disponibles en `backend/flask-services/tests/`:

```bash
python -m unittest backend/flask-services/tests/test_expert_system.py
python -m unittest backend/flask-services/tests/test_llm_first_controller.py
python -m unittest backend/flask-services/tests/test_chatbot_pain_policy.py
python -m unittest backend/flask-services/tests/test_chat_flow_etl_integration.py
python -m unittest backend/flask-services/tests/test_etl_runner.py
python -m unittest backend/flask-services/tests/test_etl_trigger.py
```

## Estructura del proyecto

```text
TFG/
├── frontend/                 # Aplicacion Next.js
├── backend/
│   ├── django_services/      # API principal (usuarios y datos clinicos)
│   └── flask-services/       # Chatbot y logica de triaje
├── docs/
│   ├── plans/                # Planes de trabajo y mejoras
│   ├── academic/             # Poster, gantt y material academico de apoyo
│   └── architecture/         # Diagramas y artefactos de arquitectura
├── nginx/                    # Configuracion de proxy y SSL
├── docker-compose.yml
└── README.md
```

## Aviso

Este sistema ofrece apoyo de triaje inicial y no sustituye la evaluacion clinica profesional.

## Licencia

Este proyecto se distribuye bajo licencia propietaria ("All rights reserved").
Consulta `LICENSE` para condiciones de uso y autorizaciones.

