"""
Database migration script for logging tables.

Run this script to create the new logging tables:
- api_request_logs
- application_logs

Usage: python -m scripts.create_logging_tables
"""

import sys
from pathlib import Path

# Add Backend to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import create_engine
from config import get_settings
from db import Base
from logger import logger
from models.logging_models import APIRequestLog, ApplicationLog

def create_logging_tables():
    """Create the logging tables in the database."""

    settings = get_settings()

    # Create database URL
    db_url = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )

    logger.info(f"Connecting to database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    logger.info("Creating logging tables...")

    # Create engine
    engine = create_engine(db_url, echo=True)

    try:
        # Create tables
        Base.metadata.create_all(bind=engine, tables=[APIRequestLog.__table__, ApplicationLog.__table__])
        logger.info("✅ Logging tables created successfully!")
        logger.info("Created tables: api_request_logs, application_logs")

    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False

    return True

if __name__ == "__main__":
    success = create_logging_tables()
    sys.exit(0 if success else 1)