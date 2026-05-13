"""
Chat Router — POST /api/chat, GET /api/chat/{job_id}
Async pattern: POST returns job_id immediately, GET polls for result
Uses Ollama + Database for intelligent agent routing
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from config import get_settings
from models.chat import ChatRequest, ChatResponse, JobResponse, JobStatusResponse
from services.ollama_router import route_to_agent
from services.oracle_agent_service import invoke_oracle_agent
from db import SessionLocal, PromptLog
from utils import job_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=JobResponse)
async def chat_submit(request: ChatRequest, current_user: User = Depends(get_current_user)) -> JobResponse:
    """
    Submit a chat query for async processing.
    Returns job_id immediately. Use GET /api/chat/{job_id} to poll for results.
    
    Requires:
    - query: The user query
    - bearer_token: Authentication token for Oracle Fusion (ONE token for ALL agents)
    
    Optional:
    - session_id: Session identifier
    - history: Conversation history
    - bearer_token: Authentication token for Oracle Fusion (optional if OAuth/basic auth is configured)
    """
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty"
        )
    
    logger.info(f"Chat query submitted: {query[:100]}")

    # ── STEP 1: Use Ollama + Database to route to correct agent ─────────────
    try:
        routing_result = await route_to_agent(query)
    except Exception as e:
        logger.error(f"Ollama routing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to route query: {str(e)}"
        )

    # Check if routing was successful
    if not routing_result["agent_code"]:
        raise HTTPException(
            status_code=400,
            detail=f"Could not route your query. {routing_result['reasoning']}. Please try rephrasing or ask about payments, subscriptions, or collections."
        )

    agent_code = routing_result["agent_code"]
    agent_name = routing_result["agent_name"]
    confidence = routing_result["confidence"]
    agent_version = routing_result.get("version")

    logger.info(f"Ollama routed to: agent_code={agent_code}, agent_name={agent_name}, version={agent_version}, confidence={confidence}")

    # ── STEP 2: Create job and return job_id ────────────────────────────────
    api_job_id = job_manager.create_job(
        query=query,
        bearer_token=request.bearer_token,
        owner_id=current_user.id,
    )
    
    # Store routing info for later
    job_manager.update_job(
        api_job_id, 
        status="QUEUED",
        result={
            "agent_code": agent_code,
            "agent_name": agent_name,
            "confidence": confidence,
            "version": agent_version,
        }
    )

    logger.info(f"Job created: {api_job_id}")

    # ── STEP 3: Log to database ─────────────────────────────────────────────
    db = SessionLocal()
    try:
        log_entry = PromptLog(
            query=query,
            endpoint="/api/chat",
            agent_id=agent_code,
            intent=agent_name,
            confidence=str(confidence)
        )
        db.add(log_entry)
        db.commit()
        logger.info(f"Prompt logged to database: agent={agent_code}")
    except Exception as e:
        logger.error(f"Failed to log to database: {e}")
        db.rollback()
    finally:
        db.close()

    # ── STEP 4: Invoke Oracle agent asynchronously ──────────────────────────
    await invoke_oracle_agent(
        query=query,
        intent=agent_name,
        confidence=confidence,
        agent_id=agent_code,
        bearer_token=request.bearer_token,
        job_id=api_job_id,
        version=agent_version,
    )

    return JobResponse(
        job_id=api_job_id,
        status="QUEUED",
        message=f"Routed to {agent_name}. Poll with GET /api/chat/{api_job_id}",
    )


@router.get("/chat/{job_id}", response_model=JobStatusResponse)
async def chat_poll(job_id: str, current_user: User = Depends(get_current_user)) -> JobStatusResponse:
    """
    Poll for the result of an async chat job.
    
    Returns:
    - status: "QUEUED" | "RUNNING" | "COMPLETE" | "ERROR"
    - result: ChatResponse (only when status == "COMPLETE")
    - error: Error message (only when status == "ERROR")
    """
    job_status = job_manager.get_job_status(job_id, owner_id=current_user.id)
    
    if not job_status:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or has expired"
        )
    
    status = job_status["status"]
    
    if status in ("QUEUED", "RUNNING"):
        return JobStatusResponse(
            job_id=job_id,
            status=status,
            message=f"Still processing... (status: {status})",
        )
    
    if status == "COMPLETE":
        result = job_manager.get_result(job_id, owner_id=current_user.id)
        if result:
            return JobStatusResponse(
                job_id=job_id,
                status="COMPLETE",
                result=result if isinstance(result, ChatResponse) else ChatResponse(**result),
            )
    
    if status == "ERROR":
        error = job_manager.get_error(job_id, owner_id=current_user.id)
        return JobStatusResponse(
            job_id=job_id,
            status="ERROR",
            error=error or "Unknown error",
        )
    
    return JobStatusResponse(
        job_id=job_id,
        status=status,
        message="Job status unknown",
    )