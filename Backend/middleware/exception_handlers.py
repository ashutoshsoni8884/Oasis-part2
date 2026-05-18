"""
Global Exception Handler for FastAPI application.
"""

import traceback
from typing import Dict, Any

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from db import SessionLocal
from logger import logger, get_request_logger
from models.logging_models import APIRequestLog


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler that logs unhandled exceptions and returns standardized responses.

    This catches any unhandled exceptions that bubble up through the middleware stack.
    """

    # Get request ID from middleware (if available)
    request_id = getattr(request.state, 'request_id', 'unknown')
    req_logger = get_request_logger(request_id)

    # Get exception details
    exc_type = type(exc).__name__
    exc_message = str(exc)
    exc_traceback = traceback.format_exc()

    # Log the exception
    req_logger.error(
        f"UNHANDLED EXCEPTION: {exc_type}: {exc_message} | "
        f"Path: {request.url.path} | Method: {request.method} | "
        f"Traceback: {exc_traceback}"
    )

    # Return standardized error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
            "message": "An unexpected error occurred. Please try again or contact support.",
            "type": exc_type
        }
    )


async def _log_exception_to_db(
    request_id: str,
    request: Request,
    error_message: str,
    status_code: int = 500
) -> None:
    """Persist exception details to api_request_logs if not already stored."""
    try:
        db = SessionLocal()
        try:
            existing = db.query(APIRequestLog).filter(APIRequestLog.request_id == request_id).first()
            if existing:
                return

            log_entry = APIRequestLog(
                request_id=request_id,
                method=request.method,
                endpoint=str(request.url),
                status_code=status_code,
                user_email=None,
                agent_team_code=None,
                request_body=None,
                response_body=None,
                error_message=error_message,
                ip_address=request.client.host if request.client else "unknown",
                duration_ms=0.0,
            )
            db.add(log_entry)
            db.commit()
        except SQLAlchemyError as exc:
            logger.error(f"Failed to persist exception request log: {exc}")
            db.rollback()
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"Exception persistence failure: {exc}")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handler for FastAPI HTTPExceptions with proper logging.
    """

    request_id = getattr(request.state, 'request_id', 'unknown')
    req_logger = get_request_logger(request_id)

    req_logger.warning(
        f"HTTP EXCEPTION: {exc.status_code} | {exc.detail} | "
        f"Path: {request.url.path} | Method: {request.method}"
    )

    await _log_exception_to_db(request_id, request, str(exc.detail), status_code=exc.status_code)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": request_id
        }
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handler for Starlette HTTPExceptions.
    """

    request_id = getattr(request.state, 'request_id', 'unknown')
    req_logger = get_request_logger(request_id)

    req_logger.warning(
        f"STARLETTE HTTP EXCEPTION: {exc.status_code} | {exc.detail} | "
        f"Path: {request.url.path} | Method: {request.method}"
    )

    await _log_exception_to_db(request_id, request, str(exc.detail), status_code=exc.status_code)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": request_id
        }
    )