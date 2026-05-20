# Oracle Agent Hub — Multi-Agent Router

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://example.com) [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com)

One-line tagline: A production-ready AI multi-agent router that orchestrates Oracle and LLM agents to handle user queries across enterprise systems.

## Overview

Oracle Agent Hub is a multi-agent orchestration platform that routes user queries to the most appropriate AI or service agent (Oracle Fusion Cloud agents, LLMs, or custom services). It provides a scalable REST API, async job handling, request logging, authentication, and configurable routing logic so enterprise teams can safely expose AI-driven functionality across business workflows.

Business problems solved:

- Centralizes access to multiple AI agents and enterprise APIs behind a single router.
- Reduces cognitive load by automatically selecting the appropriate agent for a user request.
- Enables audit logging, role-based access, and traceability for production deployments.

AI multi-agent routing capabilities:

- Intent classification and dynamic routing to domain-specific agents.
- Confidence estimation, fallback handling and retry strategies.
- Integration points for Oracle Fusion Cloud APIs and external LLM providers.

## Key Features

- Dynamic agent routing based on intent and confidence
- Multi-agent orchestration with asynchronous job management
- REST API for submitting & polling jobs
- Structured logging and audit tracking
- Robust error handling and retry policies
- Authentication support (login / register) and session persistence
- Config-driven architecture via .env and settings
- Docker-ready and production deployment patterns
- Scalable design suitable for horizontal scaling
- Oracle Fusion Cloud integration (OAuth / Basic Auth) and LLM support
- Workflow automation and follow-up suggestions

## Architecture

High-level architecture:

- Client (React UI) -> Router API (FastAPI) -> Orchestrator
- Orchestrator uses an intent classifier to select an agent/team
- Orchestrator queues an async job, invokes the chosen agent (Oracle API or LLM)
- Response is formatted, logged, and stored; client polls for completion

Request flow (step-by-step):

1. Client submits `POST /api/chat` with query and optional bearer token.
2. Router validates input and runs the intent classifier.
3. Router selects agent team and creates an async job (job_id).
4. Orchestrator invokes the chosen agent (Oracle API or LLM) with provided credentials.
5. Agent response is formatted and persisted; status updated to COMPLETE.
6. Client polls `GET /api/chat/{job_id}` to retrieve the result.

Mermaid architecture diagram:

```mermaid
flowchart LR
	A[User / UI] -->|POST /api/chat| B[FastAPI Router]
	B --> C{Intent Classifier}
	C -->|Agent A| D[Agent: Oracle Fusion]
	C -->|Agent B| E[Agent: LLM / Custom]
	D --> F[Response Formatter]
	E --> F
	F --> G[(Database / Prompt Log)]
	F --> H[Job Manager (async)]
	H -->|status| B
	B -->|GET /api/chat/{job_id}| A
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy |
| Database | PostgreSQL (psycopg / SQLAlchemy) |
| AI / LLM | Oracle AI Agent Studio, external LLMs (configurable) |
| APIs | REST (FastAPI) |
| Containerization | Docker, optional Docker Compose |
| Version Control | Git, GitHub |
| Logging | Structured logging (Python logging), audit logs in DB |
| Deployment tools | Uvicorn, Gunicorn, Kubernetes (optional) |

## Project Structure

```
.
├─ Backend/
│  ├─ main.py                # FastAPI app entrypoint
│  ├─ routers/               # API route modules (chat, agent_registry, auth)
│  ├─ services/              # Business logic: routing, oracle invocation
│  ├─ models/                # Pydantic and SQLAlchemy models
│  ├─ utils/                 # helpers: oauth, job manager, response formatting
	│  └─ db.py                # DB engine, Base, session
	├─ config.py               # Settings and .env loader
	└─ requirements.txt

├─ Frontend/
│  ├─ src/                   # React UI (Vite)
│  ├─ public/
	└─ package.json

├─ README.md
└─ .env.example
```
## detailed structure 
OASIS PART2/
 ├── Backend/ (Python/FastAPI)
 │    ├── middleware/
 │    ├── models/
 │    │    ├── agent.py (Python)
 │    │    ├── agent_registry.py (Python)
 │    │    ├── chat.py (Python)
 │    │    └── __init__.py (Python)
 │    ├── routers/
 │    │    ├── agent_registry.py (Python/FastAPI)
 │    │    ├── auth.py (Python/FastAPI)
 │    │    ├── chat.py (Python/FastAPI)
 │    │    └── __init__.py (Python)
 │    ├── scripts/
 │    │    └── update_versions.py (Python)
 │    ├── services/
 │    │    ├── agent_registry.py (Python)
 │    │    ├── intent_classifier.py (Python)
 │    │    ├── mock_agent_service.py (Python)
 │    │    ├── ollama_router.py (Python)
 │    │    ├── oracle_agent_service.py (Python)
 │    │    ├── response_formatter.py (Python)
 │    │    └── __init__.py (Python)
 │    ├── utils/
 │    │    ├── job_manager.py (Python)
 │    │    ├── oauth.py (Python)
 │    │    └── __init__.py (Python)
 │    ├── config.py (Python)
 │    ├── db.py (Python/Database)
 │    ├── main.py (Python/FastAPI)
 │    ├── modify_service.py (Python)
 │    ├── test_chat.py (Python/Pytest)
 │    ├── test_queries.py (Python/Pytest)
 │    ├── requirements.txt (Python Dependencies)
 │    ├── .env (Environment Variables)
 │    └── .env.example (Environment Variables)
 │
 ├── Frontend/ (React/Vite)
 │    ├── public/
 │    │    ├── favicon.svg (SVG Graphic)
 │    │    └── icons.svg (SVG Graphic)
 │    ├── src/
 │    │    ├── assets/
 │    │    │    ├── hero.png (PNG Image)
 │    │    │    ├── react.svg (SVG Graphic)
 │    │    │    └── vite.svg (SVG Graphic)
 │    │    ├── components/
 │    │    │    ├── AgentBadge.tsx (React/TypeScript)
 │    │    │    ├── MessageBubble.tsx (React/TypeScript)
 │    │    │    └── SuggestedFollowUps.tsx (React/TypeScript)
 │    │    ├── App.css (CSS)
 │    │    ├── App.tsx (React/TypeScript)
 │    │    ├── index.css (CSS)
 │    │    ├── main.tsx (React/TypeScript)
 │    │    └── OracleAgentHub.jsx (React/JavaScript)
 │    ├── eslint.config.js (JavaScript/ESLint Config)
 │    ├── index.html (HTML)
 │    ├── package.json (Node.js/NPM)
 │    ├── package-lock.json (Node.js/NPM)
 │    ├── tsconfig.json (TypeScript Config)
 │    ├── tsconfig.app.json (TypeScript Config)
 │    ├── tsconfig.node.json (TypeScript Config)
 │    └── vite.config.ts (Vite/TypeScript Config)
 │
 ├── New Text Document.txt (Text)
 ├── README.md (Markdown)
 └── requirements.txt (Python Dependencies)

Important files:

- `Backend/main.py`: Registers routers and middleware
- `Backend/routers/auth.py`: Login/register endpoints
- `Backend/routers/chat.py`: Submit & poll chat jobs
- `Backend/services/ollama_router.py`: Intent classification & routing logic
- `Frontend/src/OracleAgentHub.jsx`: Main React UI

## Installation

Prerequisites: Python 3.10+, Node 18+, Docker (optional), PostgreSQL

1. Clone repository

```bash
git clone https://github.com/your-org/oasis-part2.git
cd oasis-part2
```

2. Create Python virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate     # Windows PowerShell
pip install -r Backend/requirements.txt
```

3. Install frontend dependencies

```bash
cd Frontend
npm install
```

4. Copy `.env.example` to `.env` and fill values (see Environment Variables section)

5. Initialize DB (ensure PostgreSQL available and configured in .env)

```bash
# Optionally run migrations or let SQLAlchemy create tables on startup
```

## Environment Variables

| Name | Description | Example |
|---|---|---|
| DB_HOST | Postgres host | 127.0.0.1 |
| DB_PORT | Postgres port | 5432 |
| DB_NAME | Database name | oasisdb |
| DB_USER | DB username | oasis_user |
| DB_PASSWORD | DB password | secretpassword |
| FUSION_HOST | Oracle Fusion host | your-fusion-host.fa.ocs.oraclecloud.com |
| FUSION_USER | Oracle Fusion user (for Basic Auth) | oracle.user@example.com |
| FUSION_PASSWORD | Oracle Fusion password | secret |
| OAUTH_TOKEN_URL | Oracle OAuth token URL | https://.../oauth2/v1/token |
| OAUTH_CLIENT_ID | OAuth client id | abc123 |
| OAUTH_CLIENT_SECRET | OAuth client secret | s3cr3t |
| GEMINI_API_KEY | Optional LLM API key | sk-... |
| CORS_ORIGINS | Comma-separated allowed origins | http://localhost:5173 |

Keep all secrets out of source control and use a secrets manager in production.

## Running the Application

Local development (backend):

```bash
cd Backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (dev):

```bash
cd Frontend
npm run dev
```

Production (suggested):

```bash
# Use a process manager and an ASGI server like uvicorn/gunicorn
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Docker Setup

Build image:

```bash
docker build -t oracle-agent-hub:latest -f Backend/Dockerfile .
```

Run container:

```bash
docker run -d --name oracle-agent-hub -p 8000:8000 \
	-e DB_HOST=... -e DB_USER=... -e DB_PASSWORD=... oracle-agent-hub:latest
```

Compose (example `docker-compose.yml` recommended):

```yaml
version: '3.8'
services:
	web:
		build: ./Backend
		ports: ['8000:8000']
		environment:
			- DB_HOST=postgres
			- DB_USER=oasis_user
	postgres:
		image: postgres:15
		environment:
			- POSTGRES_DB=oasisdb
			- POSTGRES_USER=oasis_user
			- POSTGRES_PASSWORD=8884
```

## API Documentation (samples)

Auth: Register

- Endpoint: `POST /api/auth/register`
- Request payload:

```json
{
	"username": "alice",
	"email": "alice@example.com",
	"password": "P@ssw0rd"
}
```

- Response (200):

```json
{
	"user_id": 1,
	"username": "alice",
	"email": "alice@example.com",
	"access_token": "<jwt-or-token>"
}
```

Auth: Login

- Endpoint: `POST /api/auth/login`
- Request payload: `{ "username": "alice", "password": "P@ssw0rd" }`

Chat: Submit job

- Endpoint: `POST /api/chat`
- Request payload:

```json
{
	"query": "Show unpaid invoices for Siemens",
	"session_id": "sess_abc123",
	"history": [],
	"bearer_token": "<oracle-bearer-token>"
}
```

- Response (202):

```json
{ "job_id": "job_123", "status": "QUEUED", "message": "Routed to AR Credit" }
```

Poll job

- Endpoint: `GET /api/chat/{job_id}`
- Response when complete:

```json
{
	"job_id": "job_123",
	"status": "COMPLETE",
	"result": { "narrative": "Found 3 unpaid invoices...", "agent_id": "ar", "confidence": 0.96 }
}
```

Error responses use standard HTTP codes and JSON `{ "detail": "message" }`.

Sample curl request (submit chat):

```bash
curl -X POST http://localhost:8000/api/chat \
	-H "Content-Type: application/json" \
	-d '{"query":"Show unpaid invoices for Siemens","session_id":"sess_1","bearer_token":"<token>"}'
```

## Agent Workflow

- Agent selection: The intent classifier analyzes the query and returns a recommended agent/team and confidence score.
- Dynamic routing: If confidence exceeds threshold, the router dispatches to the selected agent; otherwise, it may fall back to a generic LLM.
- Fallback handling: On agent failure, router retries with configured backoff and can switch to alternative agents.
- Retry mechanism: Configurable retry count and exponential backoff in `utils/job_manager.py` and service invocations.
- Context management: Router passes a limited history slice (last N messages) to agents to preserve context while avoiding large payloads.

## Logging & Monitoring

- Request logging: All incoming queries recorded via `PromptLog` table
- API logging: Structured logs with timestamps and log levels
- Error logging: Exceptions captured and persisted for later analysis
- Step-level logging: Router stages (classify, queue, invoke, render) are logged for traceability
- Correlation IDs: Jobs generate `job_id` used to correlate logs across services
- Audit tracking: Authentication events (login/register) and critical actions are stored in the DB

## Error Handling

- Validation errors: FastAPI + Pydantic validation returns 4xx errors with details
- API failures: External API failures produce 5xx with retry logic where appropriate
- Retry strategies: Exponential backoff with limited retries for transient failures
- Exception handling: Centralized try/except in service layers to prevent uncaught exceptions

## Security

- Keep `.env` and secrets out of source control and use a secrets manager in production
- Authentication: Login/register endpoints provide tokens for UI session handling
- API token handling: Oracle bearer tokens are required for routing calls to Oracle APIs
- Input validation: Use Pydantic models to enforce payload schemas

## Deployment

1. Build Docker image (see Docker Setup) and push to registry
2. Deploy using your preferred orchestrator (Kubernetes, ECS, Docker Compose)
3. Use environment variables and a secrets store for credentials
4. Run healthchecks, enable monitoring (Prometheus / Grafana) and centralized logging

Production recommendations:

- Use a managed Postgres service
- Place app behind a reverse proxy and TLS termination
- Autoscale backend using Kubernetes horizontal pod autoscaler
- Secure OAuth credentials in a secrets manager

## Future Enhancements

- Persistent AI memory and user personalization
- Vector DB integration (Milvus, Pinecone) for RAG
- Multi-LLM routing and model selection
- Dashboard for live agent analytics and monitoring
- Full Kubernetes manifests and Helm chart

## Contributors

- Ashutosh Soni — Initial implementation
- Open to contributors — see CONTRIBUTING.md (optional)

## License

This project is available under the MIT License. See the LICENSE file for details.

---

Notes / Tips

- For local testing use the mock mode or provide `GEMINI_API_KEY` / `FUSION_*` credentials in `.env`.
- When adding new agents, register them via `POST /api/agent-registry/register` and provide descriptive metadata used by the intent classifier.

