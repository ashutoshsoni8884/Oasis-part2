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
- `temp_frontend_check.py`
  - Script to check if the frontend server is running on port 5173.
- `temp_health_check.py`
  - Script to check if the backend health endpoint is responding on port 8000.
- `tmp_test.txt`
  - Temporary test file, likely for debugging or scratch notes.
- `debug_invoke_response.json`
  - Sample JSON response from Oracle Fusion invoke API for debugging.
- `debug_poll_response.json`
  - Sample JSON response from Oracle Fusion polling API for debugging.

## Backend/

The `Backend` folder contains the FastAPI server, database setup, request models, orchestration services, and utility helpers.

### Backend entrypoint

- `Backend/main.py`
  - Starts the FastAPI application.
  - Loads settings from `Backend/config.py`.
  - Configures CORS to allow the React frontend at local development origins.
  - Registers the auth router from `Backend/routers/auth.py`.
  - Registers the chat router from `Backend/routers/chat.py`.
  - Registers placeholder routers for agents and agent_registry.
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
  - Defines authentication endpoints under `/api/auth`.
  - `POST /api/auth/login`
    - Accepts username and password, returns JWT access and refresh tokens.
    - Validates credentials using `Backend/services/auth_service.py`.
    - Creates audit log entry for login events.
  - `POST /api/auth/refresh`
    - Accepts refresh token, returns new access token.
    - Validates refresh token expiry and revokes old token.
  - `POST /api/auth/register`
    - Accepts username, email, password to create new user account.
    - Hashes password and stores user in database.
  - `POST /api/auth/logout`
    - Accepts refresh token and revokes it to log out user.

- `Backend/routers/agents.py`
  - Placeholder router for agent management endpoints (currently empty).

- `Backend/routers/agent_registry.py`
  - Placeholder router for agent registry management (currently empty).

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
  - Defines the User SQLAlchemy model and Pydantic schemas.
  - User model includes id, username, email, password_hash, is_active, created_at.
  - UserCreate and UserRead schemas for API operations.

- `Backend/models/auth.py`
  - Defines authentication-related Pydantic schemas.
  - Token, TokenPayload for JWT handling.
  - LoginRequest, RegisterRequest, RefreshTokenRequest, LogoutRequest for API payloads.

- `Backend/models/authorization.py`
  - Defines role-based access control models.
  - Role, Permission, UserRole, RolePermission for RBAC.
  - RefreshToken for managing refresh token lifecycle.
  - AuditLog for tracking user actions and authentication events.

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

- `Backend/services/auth_service.py`
  - Implements authentication and authorization business logic.
  - User management: get_user_by_username, get_user_by_email, create_user.
  - Authentication: authenticate_user with password verification.
  - Token management: create_refresh_token, get_refresh_token, revoke_refresh_token.
  - Audit logging: create_audit_log for tracking user actions.

- `Backend/services/token_service.py`
  - Placeholder service for token-related operations (currently empty).

### Test Files

- `Backend/test_chat.py`
  - Simple test script to send a POST request to `/api/chat` endpoint.
  - Uses httpx for async HTTP requests.
  - Tests basic chat functionality with dummy token.

- `Backend/test_queries.py`
  - Test script for multiple chat queries.
  - Tests various invoice and subscription related queries.
  - Uses httpx with longer timeout for async requests.

### Other Backend Files

- `Backend/modify_service.py`
  - Appears to be a utility script for modifying service configurations.
  - Contains regex operations, possibly for text processing or config updates.

- `Backend/debug_invoke_response.json`
  - Sample JSON response from Oracle Fusion invoke API call.

- `Backend/debug_poll_response.json`
  - Sample JSON response from Oracle Fusion polling API call.

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

### Frontend API Layer

- `Frontend/src/api/auth.js`
  - API client functions for authentication.
  - login() and register() functions that call backend `/api/auth/login` and `/api/auth/register`.
  - Handles HTTP requests with proper error handling.

### Frontend Authentication Components

- `Frontend/src/auth/AuthContext.jsx`
  - React context provider for authentication state management.
  - Manages user token, user data, and loading states.
  - Provides signIn and signUp functions that call auth API.
  - Persists authentication data in sessionStorage.

- `Frontend/src/auth/Login.jsx`
  - Login form component.
  - Collects username and password, calls AuthContext signIn.

- `Frontend/src/auth/Signup.jsx`
  - Registration form component.
  - Collects username, email, password, calls AuthContext signUp.

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

- `Backend/routers/agents.py` and `Backend/routers/agent_registry.py` are currently empty placeholders.
- The project now includes a complete authentication system with JWT tokens, user registration, login/logout, and role-based access control.
- Database models include users, roles, permissions, refresh tokens, and audit logs for security tracking.
- The backend uses SQLAlchemy for database operations with proper session management.
- Test scripts are provided for validating chat API functionality.
- Debug JSON files contain sample responses from Oracle Fusion APIs for development reference.
- The frontend includes authentication UI components with React context for state management.
- The backend uses an in-memory job store (`Backend/utils/job_manager.py`), so job state is ephemeral and resets when the backend restarts.

## Summary of file grouping

- `Backend/`: FastAPI app, config, database, model schemas, agent logic, Oracle service, authentication, authorization, async job management, test scripts.
- `Frontend/`: React + Vite UI, app bootstrap, main agent hub UI, authentication components, reusable components.
- Root files: repo metadata, dependency lists, README documentation, health check scripts, debug files.

## Recommended next steps

- Keep `Backend/config.py` updated with valid `.env` values for Oracle Fusion and Gemini.
- Run backend via `uvicorn Backend.main:app --reload`.
- Run frontend via `npm run dev` from `Frontend/`.
- Use `Frontend/src/OracleAgentHub.jsx` as the primary place to extend UI behavior.
- Use `Backend/services/agent_registry.py` to add or change supported agents and intents.
