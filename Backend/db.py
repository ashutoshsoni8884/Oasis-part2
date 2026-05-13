"""
Database setup and models.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from config import get_settings

settings = get_settings()

DATABASE_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_engine(DATABASE_URL, connect_args={'connect_timeout': 5})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class PromptLog(Base):
    __tablename__ = "prompt_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    query = Column(Text, nullable=False)
    endpoint = Column(String, nullable=False)
    agent_id = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    confidence = Column(String, nullable=True)  # Store as string for simplicity


# Create tables
try:
    # Import here to avoid circular dependency with db.Base
    from models.agent_registry import AgentRegistry
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"WARNING: Could not connect to database or create tables: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
