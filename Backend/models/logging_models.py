"""
SQLAlchemy models for centralized logging system.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean
from sqlalchemy.sql import func
from db import Base


class APIRequestLog(Base):
    """
    Logs API request/response metadata for auditing and debugging.
    """
    __tablename__ = "api_request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(36), nullable=False, index=True)  # UUID4 length
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    endpoint = Column(String(500), nullable=False)  # Full URL path
    status_code = Column(Integer, nullable=False)
    user_email = Column(String(255), nullable=True, index=True)
    agent_team_code = Column(String(100), nullable=True, index=True)
    request_body = Column(JSON, nullable=True)  # JSON request body
    response_body = Column(JSON, nullable=True)  # JSON response body (truncated if large)
    error_message = Column(Text, nullable=True)  # Error details if any
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6 support
    duration_ms = Column(Float, nullable=False)  # Response time in milliseconds
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class ApplicationLog(Base):
    """
    Structured application logs for business events and debugging.
    """
    __tablename__ = "application_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(36), nullable=True, index=True)  # Links to API request
    log_level = Column(String(10), nullable=False)  # INFO, WARNING, ERROR, etc.
    step_name = Column(String(100), nullable=False, index=True)  # e.g., "auth", "oracle_call", "agent_execution"
    message = Column(Text, nullable=False)
    payload = Column(JSON, nullable=True)  # Additional structured data
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)