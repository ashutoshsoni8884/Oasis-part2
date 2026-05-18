"""
Centralized Logging Configuration for Oasis Backend

Provides structured logging with console and rotating file output.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from config import get_settings

# Logs directory relative to this file
LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Global logger instance
logger = logging.getLogger("oasis")


class RequestIdFilter(logging.Filter):
    """Add a request_id attribute when it is missing from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "unknown"
        return True


def setup_logging(
    log_level: str = "INFO",
    enable_file_logging: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure the centralized logger with console and rotating file handlers.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Whether to enable file logging
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """

    # Clear existing handlers and filters to avoid duplicates
    logger.handlers.clear()
    logger.filters.clear()

    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(request_id)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Attach request-id filter so records without request_id still format cleanly
    request_id_filter = RequestIdFilter()
    logger.addFilter(request_id_filter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(request_id_filter)
    logger.addHandler(console_handler)

    # Rotating file handler
    if enable_file_logging:
        file_handler = logging.handlers.RotatingFileHandler(
            LOGS_DIR / "app.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(request_id_filter)
        logger.addHandler(file_handler)

    # Prevent duplicate logs from parent loggers
    logger.propagate = False

    return logger


def get_request_logger(request_id: Optional[str] = None) -> logging.LoggerAdapter:
    """
    Get a logger adapter that includes request_id in all log messages.

    Args:
        request_id: Unique request identifier

    Returns:
        LoggerAdapter with request context
    """
    return logging.LoggerAdapter(logger, {"request_id": request_id or "unknown"})


# Initialize logging on import
settings = get_settings()
setup_logging(
    log_level=settings.LOG_LEVEL if hasattr(settings, "LOG_LEVEL") else "INFO",
    enable_file_logging=settings.ENABLE_FILE_LOGGING if hasattr(settings, "ENABLE_FILE_LOGGING") else True
)