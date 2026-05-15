# routers/agent_registry.py
"""
Agent Registry API - allows dynamic registration of agent teams
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import logging

from db import get_db
from models.agent_registry import AgentRegistry
from config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-registry", tags=["agent-registry"])

# ─── Request/Response Models ────────────────────────────────────────────────

class AgentRegisterRequest(BaseModel):
    team_code: str = Field(..., description="Oracle AI Agent Team Code (e.g., ARCREDITAGENTTEAM)")
    team_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Detailed description of what this agent handles")
    version: int = Field(default=1, description="Agent team version")
    owner_team: Optional[str] = Field(None, description="Team that owns this agent")
    owner_email: Optional[str] = Field(None, description="Contact email")

class AgentRegisterResponse(BaseModel):
    message: str
    team_code: str
    status: str

class AgentListResponse(BaseModel):
    agents: list[dict]
    total_count: int

# ─── API Endpoints ─────────────────────────────────────────────────────────

@router.post("/register", response_model=AgentRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    request: AgentRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new agent team or update an existing one.
    
    This endpoint is called when:
    1. A new agent team is created in Oracle AI Agent Studio
    2. An existing agent team is updated
    3. Via CI/CD pipeline on agent deployment
    
    No authentication required for demo - add API key for production.
    """
    
    # Check if agent already exists
    existing = db.query(AgentRegistry).filter(
        AgentRegistry.team_code == request.team_code
    ).first()
    
    if existing:
        # Update existing
        existing.team_name = request.team_name
        existing.description = request.description
        existing.version = request.version
        existing.owner_team = request.owner_team
        existing.owner_email = request.owner_email
        existing.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Updated agent: {request.team_code}")
        return AgentRegisterResponse(
            message=f"Agent {request.team_code} updated successfully",
            team_code=request.team_code,
            status="UPDATED"
        )
    else:
        # Create new
        agent = AgentRegistry(
            team_code=request.team_code,
            team_name=request.team_name,
            description=request.description,
            version=request.version,
            owner_team=request.owner_team,
            owner_email=request.owner_email
        )
        db.add(agent)
        db.commit()
        
        logger.info(f"Registered new agent: {request.team_code}")
        return AgentRegisterResponse(
            message=f"Agent {request.team_code} registered successfully",
            team_code=request.team_code,
            status="CREATED"
        )


@router.get("/list", response_model=AgentListResponse)
async def list_agents(
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all registered agent teams.
    Used to fetch available registered agents.
    """
    
    query = db.query(AgentRegistry)
    
    if not include_inactive:
        query = query.filter(AgentRegistry.is_active == True)
    
    agents = query.all()
    
    return AgentListResponse(
        agents=[
            {
                "team_code": agent.team_code,
                "team_name": agent.team_name,
                "description": agent.description,
                "version": agent.version,
                "is_active": agent.is_active
            }
            for agent in agents
        ],
        total_count=len(agents)
    )


@router.delete("/{team_code}")
async def deregister_agent(
    team_code: str,
    hard_delete: bool = False,
    db: Session = Depends(get_db)
):
    """
    Remove or deactivate an agent team.
    - hard_delete=True: Completely remove from database
    - hard_delete=False: Soft delete (set is_active=False)
    """
    
    agent = db.query(AgentRegistry).filter(
        AgentRegistry.team_code == team_code
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {team_code} not found")
    
    if hard_delete:
        db.delete(agent)
        message = f"Agent {team_code} permanently deleted"
    else:
        agent.is_active = False
        message = f"Agent {team_code} deactivated"
    
    db.commit()
    
    return {"message": message, "team_code": team_code}


@router.put("/{team_code}/reactivate")
async def reactivate_agent(
    team_code: str,
    db: Session = Depends(get_db)
):
    """Reactivate a previously deactivated agent"""
    
    agent = db.query(AgentRegistry).filter(
        AgentRegistry.team_code == team_code
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {team_code} not found")
    
    agent.is_active = True
    db.commit()
    
    return {"message": f"Agent {team_code} reactivated", "team_code": team_code}