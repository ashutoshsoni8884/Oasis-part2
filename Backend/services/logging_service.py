"""
Logging Service - Helper functions for database logging operations.
"""

import logging
from typing import Dict, Any, Optional

from sqlalchemy.exc import SQLAlchemyError
from db import SessionLocal
from models.logging_models import ApplicationLog
from logger import logger


class LoggingService:
    """
    Service for structured database logging with error handling.
    """

    @staticmethod
    async def log_application_step(
        request_id: str,
        level: str,
        step_name: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a business event or step to the database.

        This should only be used for important business events:
        - Authentication events
        - Oracle Fusion API calls
        - AI agent execution
        - External API calls
        - Database failures
        - Authorization failures

        Args:
            request_id: Unique request identifier
            level: Log level (INFO, WARNING, ERROR, etc.)
            step_name: Name of the business step (e.g., "auth", "oracle_call")
            message: Log message
            payload: Optional structured data (will be JSON serialized)
        """
        try:
            # Create log entry
            log_entry = ApplicationLog(
                request_id=request_id,
                log_level=level.upper(),
                step_name=step_name,
                message=message,
                payload=payload
            )

            # Use a new session for this operation
            db = SessionLocal()
            try:
                db.add(log_entry)
                db.commit()
                logger.debug(f"Logged application step: {step_name} - {message}")
            except SQLAlchemyError as e:
                logger.error(f"Failed to log application step to database: {e}")
                db.rollback()
                # Don't re-raise - logging failures shouldn't crash the app
            finally:
                db.close()

        except Exception as e:
            # Last resort - log to file only if DB logging completely fails
            logger.error(f"Critical logging service error: {e}")

    @staticmethod
    def log_sync_application_step(
        request_id: str,
        level: str,
        step_name: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Synchronous version of log_application_step for use in sync contexts.
        """
        try:
            # Create log entry
            log_entry = ApplicationLog(
                request_id=request_id,
                log_level=level.upper(),
                step_name=step_name,
                message=message,
                payload=payload
            )

            # Use a new session for this operation
            db = SessionLocal()
            try:
                db.add(log_entry)
                db.commit()
                logger.debug(f"Logged application step: {step_name} - {message}")
            except SQLAlchemyError as e:
                logger.error(f"Failed to log application step to database: {e}")
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Critical logging service error: {e}")


# Global instance
logging_service = LoggingService()


# Convenience functions
async def log_application_step(
    request_id: str,
    level: str,
    step_name: str,
    message: str,
    payload: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function for async logging."""
    await logging_service.log_application_step(request_id, level, step_name, message, payload)


def log_application_step_sync(
    request_id: str,
    level: str,
    step_name: str,
    message: str,
    payload: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function for sync logging."""
    logging_service.log_sync_application_step(request_id, level, step_name, message, payload)