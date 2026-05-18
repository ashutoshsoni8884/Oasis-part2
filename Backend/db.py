"""
Database setup and models.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import get_settings

settings = get_settings()

DATABASE_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_engine(DATABASE_URL, connect_args={'connect_timeout': 5})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

from models.agent_registry import AgentRegistry


class PromptLog(Base):
    __tablename__ = "prompt_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    query = Column(Text, nullable=False)
    endpoint = Column(String, nullable=False)
    agent_id = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    confidence = Column(String, nullable=True)  # Store as string for simplicity


# Import models so SQLAlchemy can create tables for all registered models.
import models.user  # noqa: F401
import models.authorization  # noqa: F401

# Create tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    import logging
    logging.getLogger("oasis").warning(f"Could not connect to database or create tables: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()