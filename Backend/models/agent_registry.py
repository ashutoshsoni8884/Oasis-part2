# models/agent_registry.py
"""
Database model for agent registry - stores all Oracle AI Agent Teams
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from Backend.db import Base

class AgentRegistry(Base):
    __tablename__ = "agent_registry"
    
    id = Column(Integer, primary_key=True, index=True)
    team_code = Column(String(200), unique=True, nullable=False, index=True)
    team_name = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)  # Used for routing/agent metadata
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional metadata
    owner_team = Column(String(200), nullable=True)
    owner_email = Column(String(200), nullable=True)