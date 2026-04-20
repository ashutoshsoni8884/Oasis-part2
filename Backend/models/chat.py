"""
Request / Response schemas for the chat endpoint.
"""

from pydantic import BaseModel


# ─── Request ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    history: list[dict] | None = None


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
    kpis: list[KPI] | None = None
    columns: list[str] | None = None
    rows: list[list[str]] | None = None
    charts: list[ChartData] | None = None
    follow_ups: list[str] | None = None
    fallback: bool = False
    message: str | None = None
