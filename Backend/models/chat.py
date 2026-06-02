"""
Request / Response schemas for the chat endpoint.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ─── Request ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    history: list[dict] | None = None
    bearer_token: str | None = None
    job_id: str | None = None
    force_agent_id: str | None = None
    conversation_id: str | None = None  # Oracle's conversation ID for multi-turn agent conversations


# ─── Response sub-models ────────────────────────────────────────────────────────

class KPI(BaseModel):
    label: str
    value: str
    trend: str | None = None
    up: bool | None = None  # True = good, False = bad, None = neutral


class ChartDataset(BaseModel):
    label: str
    data: list[float | int]
    color: str | None = None


class ChartData(BaseModel):
    chart_type: str  # "bar" | "pie" | "line" | "gauge" | "doughnut"
    title: str
    labels: list[str]
    datasets: list[ChartDataset]


class ChatResponse(BaseModel):
    success: bool
    intent: str | None = None
    confidence: float | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    narrative: str | None = None
    html: str | None = None
    kpis: list[KPI] | None = None
    columns: list[str] | None = None
    rows: list[list[str]] | None = None
    charts: list[ChartData] | None = None
    follow_ups: list[str] | None = None
    fallback: bool = False
    message: str | None = None
    conversation_id: str | None = None  # Oracle's conversation ID to maintain state


# ─── Async Job Responses ────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    """Response from POST /api/chat — returns job_id for polling"""
    job_id: str
    status: str  # "QUEUED"
    message: str | None = None
    conversation_id: str | None = None  # Return conversation_id for client to store


class JobStatusResponse(BaseModel):
    """Response from GET /api/chat/{job_id} during polling"""
    job_id: str
    status: str  # "QUEUED" | "RUNNING" | "COMPLETE" | "ERROR"
    message: str | None = None
    result: ChatResponse | None = None  # Only present when status == "COMPLETE"
    error: str | None = None  # Only present when status == "ERROR"
    conversation_id: str | None = None  # Return conversation_id for ongoing conversations


class JobResultResponse(BaseModel):
    """Final result response when job is COMPLETE"""
    job_id: str
    status: str  # "COMPLETE"
    result: ChatResponse
    conversation_id: str | None = None


# ─── Additional Models for Workflow Management ─────────────────────────────────

class WorkflowStatusResponse(BaseModel):
    """Response for checking workflow status"""
    session_id: str
    active_agent: str | None = None
    conversation_id: str | None = None
    is_active: bool
    message_count: int | None = None
    expires_in_seconds: int | None = None


class EndWorkflowResponse(BaseModel):
    """Response for ending a workflow"""
    success: bool
    message: str
    session_id: str