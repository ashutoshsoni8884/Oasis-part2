"""
Agent metadata model — mirrors the frontend AGENTS configuration.
"""

from pydantic import BaseModel


class AgentConfig(BaseModel):
    id: str
    name: str
    short_name: str
    icon: str
    color: str
    bg: str
    intents: list[str]
    description: str
    # Oracle AI Agent Studio mapping (used in real mode)
    oracle_agent_team_code: str | None = None
