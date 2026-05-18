"""
FastAPI Middleware for centralized request/response logging.
"""

import json
import time
import traceback
from typing import Callable, Dict, Any, Optional
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from config import get_settings
from db import SessionLocal
from logger import logger, get_request_logger
from models.logging_models import APIRequestLog
from services.logging_service import log_application_step
from utils.security import get_current_user_optional


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all API requests and responses to database and files.

    Features:
    - Generates unique request_id for tracing
    - Captures request/response metadata
    - Logs to database (api_request_logs table)
    - Handles exceptions gracefully
    - Redacts sensitive data
    - Performance protections
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        self.max_body_size = getattr(self.settings, 'LOG_MAX_BODY_SIZE', 10000)  # 10KB default

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request through the logging middleware.
        """
        # Generate unique request ID
        request_id = str(uuid4())
        request.state.request_id = request_id

        # Get request logger with context
        req_logger = get_request_logger(request_id)

        start_time = time.time()

        # Extract request metadata
        method = request.method
        url = str(request.url)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Extract and sanitize request body
        request_body = await self._extract_request_body(request)

        # Get user info (if authenticated)
        user_email = None
        try:
            current_user = await get_current_user_optional(request)
            if current_user:
                user_email = getattr(current_user, "username", None) or getattr(current_user, "email", None)
        except Exception:
            # Don't fail if user extraction fails
            pass

        # Extract agent_team_code from request body if present
        agent_team_code = self._extract_agent_team_code(request_body)

        req_logger.info(f"REQUEST: {method} {url} | IP: {client_ip} | User: {user_email or 'anonymous'}")

        response = None
        error_message = None

        try:
            # Process the request
            response = await call_next(request)

            # Extract response body for logging (safely)
            response_body = await self._extract_response_body(response)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log successful request
            req_logger.info(
                f"RESPONSE: {response.status_code} | Duration: {duration_ms:.2f}ms | "
                f"Agent: {agent_team_code or 'none'}"
            )

        except Exception as exc:
            # Handle exceptions
            duration_ms = (time.time() - start_time) * 1000
            error_message = str(exc)
            traceback_str = traceback.format_exc()

            req_logger.error(
                f"EXCEPTION: {type(exc).__name__}: {error_message} | "
                f"Duration: {duration_ms:.2f}ms | Traceback: {traceback_str}"
            )

            # Return error response
            response = JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "message": "An unexpected error occurred"
                }
            )
            response_body = response.body.decode() if hasattr(response, 'body') else None

        # Log to database (async and safe)
        if getattr(self.settings, 'ENABLE_DB_LOGGING', True):
            await self._log_to_database(
                request_id=request_id,
                method=method,
                endpoint=url,
                status_code=response.status_code if response else 500,
                user_email=user_email,
                agent_team_code=agent_team_code,
                request_body=request_body,
                response_body=response_body,
                error_message=error_message,
                ip_address=client_ip,
                duration_ms=duration_ms if 'duration_ms' in locals() else (time.time() - start_time) * 1000
            )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check X-Forwarded-For header first (for proxies/load balancers)
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # Take the first IP if multiple are present
            return x_forwarded_for.split(",")[0].strip()

        # Fall back to X-Real-IP
        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip:
            return x_real_ip

        # Fall back to client host
        return request.client.host if request.client else "unknown"

    async def _extract_request_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """Safely extract and sanitize request body."""
        try:
            # Only extract body for POST/PUT/PATCH requests
            if request.method not in ["POST", "PUT", "PATCH"]:
                return None

            # Skip if content-type suggests binary data
            content_type = request.headers.get("content-type", "").lower()
            if any(skip_type in content_type for skip_type in ["multipart", "binary", "octet-stream"]):
                return {"skipped": "binary_data"}

            # Read body
            body_bytes = await request.body()

            # Skip if body is too large
            if len(body_bytes) > self.max_body_size:
                return {"truncated": f"body_too_large_{len(body_bytes)}_bytes"}

            # Parse JSON safely
            if body_bytes:
                try:
                    body_json = json.loads(body_bytes.decode())
                    # Redact sensitive fields
                    return self._redact_sensitive_data(body_json)
                except json.JSONDecodeError:
                    # Not JSON, store as string
                    return {"raw_body": body_bytes.decode()[:self.max_body_size]}

            return None

        except Exception as e:
            logger.warning(f"Failed to extract request body: {e}")
            return {"error": "failed_to_extract"}

    async def _extract_response_body(self, response: Response) -> Optional[Dict[str, Any]]:
        """Safely extract response body for logging."""
        try:
            # Skip if response is streaming
            if hasattr(response, 'body_iterator') or getattr(response, 'is_streaming', False):
                return {"skipped": "streaming_response"}

            # Get response body
            if hasattr(response, 'body'):
                body_bytes = response.body
            elif hasattr(response, 'render'):
                # For JSONResponse and similar
                body_bytes = response.render(response.body)
            else:
                return None

            # Skip if too large
            if len(body_bytes) > self.max_body_size:
                return {"truncated": f"body_too_large_{len(body_bytes)}_bytes"}

            # Parse JSON safely
            if body_bytes:
                try:
                    body_str = body_bytes.decode()
                    body_json = json.loads(body_str)
                    return self._redact_sensitive_data(body_json)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return {"raw_body": body_bytes.decode()[:self.max_body_size]}

            return None

        except Exception as e:
            logger.warning(f"Failed to extract response body: {e}")
            return {"error": "failed_to_extract"}

    def _redact_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive fields from request/response data."""
        if not isinstance(data, dict):
            return data

        sensitive_fields = {
            "password", "token", "authorization", "bearer_token", "api_key",
            "secret", "key", "auth", "credential", "session_id"
        }

        redacted = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_fields):
                redacted[key] = "***REDACTED***"
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive_data(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = value

        return redacted

    def _extract_agent_team_code(self, request_body: Optional[Dict[str, Any]]) -> Optional[str]:
        """Extract agent_team_code from request body if present."""
        if not request_body:
            return None

        # Check common locations for agent_team_code
        possible_keys = ["agent_team_code", "agent_code", "team_code", "agent"]
        for key in possible_keys:
            if key in request_body:
                return str(request_body[key])

        return None

    async def _log_to_database(
        self,
        request_id: str,
        method: str,
        endpoint: str,
        status_code: int,
        user_email: Optional[str],
        agent_team_code: Optional[str],
        request_body: Optional[Dict[str, Any]],
        response_body: Optional[Dict[str, Any]],
        error_message: Optional[str],
        ip_address: str,
        duration_ms: float
    ) -> None:
        """Log request metadata to database safely."""
        try:
            log_entry = APIRequestLog(
                request_id=request_id,
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                user_email=user_email,
                agent_team_code=agent_team_code,
                request_body=request_body,
                response_body=response_body,
                error_message=error_message,
                ip_address=ip_address,
                duration_ms=duration_ms
            )

            # Use new session
            db = SessionLocal()
            try:
                db.add(log_entry)
                db.commit()
                logger.debug(f"Logged API request to database: {request_id}")
            except Exception as e:
                logger.error(f"Failed to log API request to database: {e}")
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            # Last resort - don't crash the app
            logger.error(f"Critical database logging error: {e}")