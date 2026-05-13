"""
Agents Router — exposes allowed Oracle agent teams for the current user.

GET /api/agents
  - Authenticated (JWT)
  - Returns the list of agent_team_code values the user can access.
"""

from fastapi import APIRouter, Depends

from Backend.models.user import User
from Backend.services.agent_service import get_allowed_agents, get_agent_config
from Backend.utils.security import get_current_user

router = APIRouter(prefix="/api", tags=["agents"])


@router.get("/agents")
async def list_agents(current_user: User = Depends(get_current_user)) -> dict:
    """
    Return all allowed agents for the current user.

    Response:
      {
        "agents": [
          { "agent_team_code": "ARCREDITAGENTTEAM" },
          ...
        ]
      }
    """
    allowed_codes = get_allowed_agents(current_user)
    agents = [get_agent_config(code) for code in allowed_codes]
    return {"agents": agents}

