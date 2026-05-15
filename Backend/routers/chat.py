"""
Chat Router — POST /api/chat, GET /api/chat/{job_id}
Async pattern: POST returns job_id immediately, GET polls for result
"""

import logging
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException

from config import get_settings
from db import PromptLog, SessionLocal
from models.chat import ChatRequest, ChatResponse, JobResponse, JobStatusResponse
from models.user import User
from services import intent_classifier
from services.agent_service import validate_agent_access
from services.mock_agent_service import get_mock_response
from services.oracle_agent_service import invoke_oracle_agent
from utils import job_manager
from utils.security import get_current_user

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
    settings = get_settings()
    request_id = str(uuid4())

    message = (request.message or request.query or "").strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )
    
    logger.info(
        {
            "event": "chat_submit",
            "request_id": request_id,
            "user_id": getattr(current_user, "id", None),
            "username": getattr(current_user, "username", None),
            "message_preview": message[:120],
        }
    )

    # ── Step 1: routing via Gemini ────────────────────────────────────────────
    try:
        agent_team_code = await intent_classifier.classify_intent(message)
    except Exception as e:
        logger.error({"event": "intent_classification_failed", "request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to classify query intent")

    # ── Step 2: resolve + authorize agent_team_code ───────────────────────────
    if request.agent_team_code:
        effective_team_code = validate_agent_access(current_user, request.agent_team_code)
    else:
        effective_team_code = validate_agent_access(current_user, agent_team_code)

    # ── STEP 2: Create job and return job_id ────────────────────────────────
    api_job_id = job_manager.create_job(
        query=message,
        bearer_token=request.bearer_token,
        owner_id=current_user.id,
    )
    
    # Store routing info for later
    job_manager.update_job(
        api_job_id, 
        status="QUEUED",
        result={
            "agent_team_code": effective_team_code,
        }
    )

    logger.info(f"Job created: {api_job_id}")

    # ── STEP 3: Log to database ─────────────────────────────────────────────
    db = SessionLocal()
    try:
        log_entry = PromptLog(
            query=message,
            endpoint="/api/chat",
            agent_id=agent_id,
            intent=intent,
            confidence=str(confidence)
        )
        db.add(log_entry)
        db.commit()
        logger.info(f"Prompt logged to database: agent={agent_id}")
    except Exception as e:
        logger.error(f"Failed to log to database: {e}")
        db.rollback()
    finally:
        db.close()

    # ── Step 4: Invoke agent asynchronously (mock or Oracle) ─────────────────
    if settings.MOCK_MODE:
        response = await get_mock_response(agent_id, intent, confidence, message)
        job_manager.update_job(
            api_job_id,
            status="COMPLETE",
            result=response.dict() if hasattr(response, "dict") else response,
        )
    else:
        await invoke_oracle_agent(
            query=message,
            intent=intent,
            confidence=confidence,
            agent_id=agent_id,
            bearer_token=request.bearer_token,
            job_id=api_job_id,
            agent_team_code=effective_team_code,
        )

    return JobResponse(
        job_id=api_job_id,
        status="QUEUED",
        message=f"Request queued. Poll with GET /api/chat/{api_job_id}",
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