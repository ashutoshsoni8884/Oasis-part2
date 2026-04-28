# Oasis part 2 — File Hierarchy and Architecture

This document explains the project structure, each file's purpose, and how backend and frontend components interconnect.

## Root Files

- `README.md`
  - Existing project README with a brief title and description.
- `README_STRUCTURE.md`
  - This new file describing the file hierarchy, file responsibilities, and connections.
- `requirements.txt`
  - Python dependencies for the backend and shared environment tools.
- `New Text Document.txt`
  - Unused text file. Likely scratch or placeholder content.
- `practics.py`
  - Local Python file; appearance suggests practice or experiment code. Not part of the main app flow.

## Backend/

The `Backend` folder contains the FastAPI server, database setup, request models, orchestration services, and utility helpers.

### Backend entrypoint

- `Backend/main.py`
  - Starts the FastAPI application.
  - Loads settings from `Backend/config.py`.
  - Configures CORS to allow the React frontend at local development origins.
  - Registers the chat router from `Backend/routers/chat.py`.
  - Provides a `/api/health` endpoint for health checks.

### Backend configuration

- `Backend/config.py`
  - Defines the `Settings` class using `pydantic_settings.BaseSettings`.
  - Loads environment variables from `Backend/.env` via `python-dotenv` style config.
  - Contains Oracle Fusion, Gemini, database, and CORS-related configuration values.
  - Exposes `get_settings()` as a cached singleton.

### Database layer

- `Backend/db.py`
  - Builds a SQLAlchemy engine using `Settings` values.
  - Creates `SessionLocal` for database sessions.
  - Defines the `PromptLog` SQLAlchemy model for storing incoming query logs.
  - Creates database tables on startup.
  - Provides `get_db()` generator for dependency injection if needed.

### FastAPI routers

- `Backend/routers/chat.py`
  - Defines chat endpoints under `/api`.
  - `POST /api/chat`
    - Accepts user text, optional history and session metadata, and a required bearer token.
    - Classifies intent using `Backend/services/intent_classifier.py`.
    - Selects a matching agent from `Backend/services/agent_registry.py`.
    - Creates an async job through `Backend/utils/job_manager.py`.
    - Logs the request via `Backend/db.py`.
    - Invokes Oracle Fusion asynchronously through `Backend/services/oracle_agent_service.py`.
    - Returns a `job_id` immediately so the frontend can poll.
  - `GET /api/chat/{job_id}`
    - Polls the in-memory job manager.
    - Returns job status, completed results, or error details.

- `Backend/routers/auth.py`
  - Empty file in this repo.
  - Placeholder for future authentication-related router logic.

### Models

- `Backend/models/chat.py`
  - Defines request/response schemas using Pydantic.
  - `ChatRequest` describes the POST body for `/api/chat`.
  - `ChatResponse` defines the structured response returned to the frontend.
  - `JobResponse` and `JobStatusResponse` support the async job polling flow.

- `Backend/models/agent.py`
  - Defines `AgentConfig`, the metadata structure for each Oracle agent.
  - Agent metadata includes ID, display name, intents, icon, colors, description, and optional Oracle mapping.

- `Backend/models/role.py`
  - Empty in this repository.
  - Placeholder for future role-based or permission modeling.

- `Backend/models/user.py`
  - Empty in this repository.
  - Placeholder for future user model definitions.

### Services

- `Backend/services/intent_classifier.py`
  - Classifies user input into a domain intent.
  - Primary path uses Google Gemini LLM if `GEMINI_API_KEY` is configured.
  - If Gemini is unavailable, it falls back to regex-based intent matching.
  - Uses `Backend/services.agent_registry.py` to validate agent mapping.
  - Returns an object containing `intent`, `agent_id`, `confidence`, and `reasoning`.

- `Backend/services/agent_registry.py`
  - Defines the list of supported agents and their intent mappings.
  - Provides lookup helpers:
    - `get_agent(agent_id)`
    - `get_agent_for_intent(intent)`
    - `get_all_agents()`
  - This is the central source of truth for agent metadata in the backend.

- `Backend/services/oracle_agent_service.py`
  - Implements the async Oracle Fusion invocation flow.
  - Sends the user query to Oracle AI Agent Studio using `/invokeAsync`.
  - Starts a background polling task to check `/status/{jobId}`.
  - Updates the in-memory job manager when the Oracle job completes or errors.
  - Uses `Backend/utils/oauth.py` for OAuth token acquisition or `Basic Auth` fallback.
  - Converts raw Oracle output into frontend-friendly shape using `Backend/services/response_formatter.py`.

- `Backend/services/response_formatter.py`
  - Transforms raw Oracle agent output into `ChatResponse` objects.
  - Detects HTML vs plain-text responses.
  - Attaches generated follow-up suggestions based on the classified intent.
  - Normalizes fields such as `agent_name`, `narrative`, `html`, and `follow_ups`.

- `Backend/services/mock_agent_service.py`
  - Not read directly, but likely contains local mock response logic.
  - In this repo, real Oracle mode is active and mock mode is commented out.

### Utilities

- `Backend/utils/job_manager.py`
  - In-memory async job store for `POST /api/chat` + `GET /api/chat/{job_id}`.
  - Creates jobs with UUIDs, stores status, result, and expiration metadata.
  - Supports `QUEUED`, `RUNNING`, `COMPLETE`, and `ERROR` states.
  - Used by `Backend/routers/chat.py` and `Backend/services/oracle_agent_service.py`.

- `Backend/utils/oauth.py`
  - Requests OAuth bearer tokens from Oracle identity service.
  - Caches tokens until near expiry.
  - Builds Basic Auth headers from `FUSION_USER` / `FUSION_PASSWORD` if OAuth is not configured.

- `Backend/utils/security.py`
  - Not read directly, likely contains security-related utilities.
  - Could be used later for auth / token verification.

## Frontend/

The `Frontend` folder contains the React + Vite UI layer that calls the backend router.

### Frontend root files

- `Frontend/package.json`
  - Defines the UI dependencies and build scripts.
  - Uses React 19, Vite, Tailwind CSS, and ESLint.

- `Frontend/README.md`
  - Default Vite React README template.
  - Not specific to the Oracle Agent app.

- `Frontend/vite.config.ts`
  - Vite configuration for the frontend app.
  - Required to build and serve the React application.

- `Frontend/tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`
  - TypeScript configuration files.
  - Control compiler settings, project references, and module resolution.

- `Frontend/index.html`
  - HTML entry point for the React app.
  - References the root `div` where React renders.

### Frontend source folder

- `Frontend/src/main.tsx`
  - Bootstrap file for the React application.
  - Imports `App` and renders it into the DOM root.

- `Frontend/src/App.tsx`
  - Root React component.
  - Simply renders `OracleAgentHub`.

- `Frontend/src/OracleAgentHub.jsx`
  - Main UI component for the agent hub.
  - Contains the full user interaction flow:
    - Builds and submits `/api/chat` requests.
    - Polls backend job status until completion.
    - Maps backend snake_case payloads into frontend camelCase state.
    - Presents agent conversation output, follow-ups, KPIs, tables, and charts.
  - Also includes mock intent patterns and fallback UI logic in case the backend is unavailable.

### Frontend UI components

These files are small reusable components that support UI rendering.

- `Frontend/src/components/AgentBadge.tsx`
  - Displays a small status badge for an agent or user.

- `Frontend/src/components/MessageBubble.tsx`
  - Renders chat bubbles for user and assistant messages.

- `Frontend/src/components/SuggestedFollowUps.tsx`
  - Renders clickable follow-up suggestion buttons.

## How the backend and frontend connect

1. User enters a query in the React UI.
2. `Frontend/src/OracleAgentHub.jsx` calls `POST http://127.0.0.1:8000/api/chat`.
3. `Backend/routers/chat.py` receives the request and validates the input.
4. The backend uses `intent_classifier.py` to classify the query intent.
5. The matching agent is resolved via `agent_registry.py`.
6. A new async job is created in `job_manager.py`.
7. The backend calls Oracle Fusion via `oracle_agent_service.py`.
8. Oracle Fusion responds with a job ID; the backend polls until the result is ready.
9. When complete, `response_formatter.py` shapes the Oracle result into `ChatResponse`.
10. The frontend polls `GET /api/chat/{job_id}` until the status becomes `COMPLETE`.
11. The UI displays the final content, charts, tables, and follow-ups.

## Notes about current repo contents

- `Backend/routers/auth.py`, `Backend/models/role.py`, and `Backend/models/user.py` are currently empty.
- The project is configured for live Oracle Fusion / Gemini integration, but it still contains fallback/mock patterns.
- `Frontend/src/OracleAgentHub.jsx` includes a small mock router and intent detection logic used for local UI demonstration and error handling.
- The backend uses an in-memory job store (`Backend/utils/job_manager.py`), so job state is ephemeral and resets when the backend restarts.

## Summary of file grouping

- `Backend/`: FastAPI app, config, database, model schemas, agent logic, Oracle service, async job management.
- `Frontend/`: React + Vite UI, app bootstrap, main agent hub UI, optional reusable components.
- Root files: repo metadata, dependency lists, and README documentation.

## Recommended next steps

- Keep `Backend/config.py` updated with valid `.env` values for Oracle Fusion and Gemini.
- Run backend via `uvicorn Backend.main:app --reload`.
- Run frontend via `npm run dev` from `Frontend/`.
- Use `Frontend/src/OracleAgentHub.jsx` as the primary place to extend UI behavior.
- Use `Backend/services/agent_registry.py` to add or change supported agents and intents.
