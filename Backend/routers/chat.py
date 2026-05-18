"""
Chat Router — POST /api/chat, GET /api/chat/{job_id}
Async pattern: POST returns job_id immediately, GET polls for result
"""

from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request

from config import get_settings
from db import PromptLog, SessionLocal
from logger import get_request_logger
from models.chat import ChatRequest, ChatResponse, JobResponse, JobStatusResponse
from models.user import User
from services import intent_classifier
from services.agent_service import validate_agent_access
from services.logging_service import log_application_step
from services.mock_agent_service import get_mock_response
from services.oracle_agent_service import invoke_oracle_agent
from utils import job_manager
from utils.security import get_current_user

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=JobResponse)
async def chat_submit(
    request: ChatRequest,
    fastapi_request: Request,
    current_user: User = Depends(get_current_user)
) -> JobResponse:
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
    # Get request_id from middleware
    request_id = getattr(fastapi_request.state, 'request_id', str(uuid4()))
    req_logger = get_request_logger(request_id)

    message = (request.message or request.query or "").strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    req_logger.info(
        f"Chat request received | User: {current_user.username} | "
        f"Message: {message[:100]}{'...' if len(message) > 100 else ''}"
    )

    # ── Step 1: routing via Ollama + database-backed agent registry ─────────
    try:
        classification = await intent_classifier.classify_intent(message)
    except Exception as e:
        req_logger.error(f"Intent classification failed: {e}")
        await log_application_step(
            request_id, "ERROR", "intent_classification",
            f"Failed to classify intent: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Failed to classify query intent")

    agent_team_code = classification.get("agent_team_code")
    agent_name = classification.get("agent_name")
    confidence = classification.get("confidence", 0.0)
    reasoning = classification.get("reasoning", "")

    req_logger.info(
        f"Intent classified | Agent: {agent_team_code} | "
        f"Confidence: {confidence:.2f} | Reasoning: {reasoning}"
    )

    await log_application_step(
        request_id, "INFO", "intent_classification",
        f"Classified query to agent {agent_team_code}",
        {
            "agent_team_code": agent_team_code,
            "agent_name": agent_name,
            "confidence": confidence,
            "reasoning": reasoning
        }
    )

    if request.agent_team_code:
        effective_team_code = validate_agent_access(current_user, request.agent_team_code)
        req_logger.info(f"Using user-specified agent: {effective_team_code}")
    else:
        if not agent_team_code:
            req_logger.warning(f"No agent matched query: {reasoning}")
            raise HTTPException(status_code=400, detail=reasoning or "Could not confidently match your query to an agent.")
        effective_team_code = validate_agent_access(current_user, agent_team_code)

    # Log agent access validation
    await log_application_step(
        request_id, "INFO", "agent_access_validation",
        f"Validated access to agent {effective_team_code}",
        {"agent_team_code": effective_team_code, "user": current_user.username}
    )

    api_job_id = job_manager.create_job(
        query=message,
        bearer_token=request.bearer_token,
        owner_id=current_user.id,
    )

    job_manager.update_job(
        api_job_id,
        status="QUEUED",
        result={
            "agent_team_code": effective_team_code,
            "agent_name": agent_name,
            "confidence": confidence,
            "reasoning": reasoning,
        }
    )

    req_logger.info(f"Job created: {api_job_id} for agent {effective_team_code}")

    db = SessionLocal()
    try:
        log_entry = PromptLog(
            query=message,
            endpoint="/api/chat",
            agent_id=effective_team_code,
            intent=agent_name or "",
            confidence=str(confidence)
        )
        db.add(log_entry)
        db.commit()
        req_logger.debug(f"Prompt logged to database: agent={effective_team_code}")
    except Exception as e:
        req_logger.error(f"Failed to log to database: {e}")
        db.rollback()
    finally:
        db.close()

    if settings.MOCK_MODE:
        req_logger.info(f"Using mock response for agent {effective_team_code}")
        response = await get_mock_response(effective_team_code, agent_name or "", confidence, message)
        job_manager.update_job(
            api_job_id,
            status="COMPLETE",
            result=response.dict() if hasattr(response, "dict") else response,
        )
        await log_application_step(
            request_id, "INFO", "mock_agent_execution",
            f"Mock response generated for agent {effective_team_code}",
            {"agent_team_code": effective_team_code, "job_id": api_job_id}
        )
    else:
        req_logger.info(f"Invoking Oracle agent {effective_team_code}")
        await log_application_step(
            request_id, "INFO", "oracle_agent_invocation",
            f"Starting Oracle agent execution for {effective_team_code}",
            {
                "agent_team_code": effective_team_code,
                "job_id": api_job_id,
                "bearer_token_present": bool(request.bearer_token)
            }
        )

        await invoke_oracle_agent(
            query=message,
            intent=agent_name or "",
            confidence=confidence,
            agent_id=effective_team_code,
            bearer_token=request.bearer_token,
            job_id=api_job_id,
            agent_team_code=effective_team_code,
            request_id=request_id,
        )

    return JobResponse(
        job_id=api_job_id,
        status="QUEUED",
        message=f"Request queued. Poll with GET /api/chat/{api_job_id}",
    )


@router.get("/chat/{job_id}", response_model=JobStatusResponse)
async def chat_poll(
    job_id: str,
    fastapi_request: Request,
    current_user: User = Depends(get_current_user)
) -> JobStatusResponse:
    """
    Poll for the result of an async chat job.

    Returns:
    - status: "QUEUED" | "RUNNING" | "COMPLETE" | "ERROR"
    - result: ChatResponse (only when status == "COMPLETE")
    - error: Error message (only when status == "ERROR")
    """
    request_id = getattr(fastapi_request.state, 'request_id', 'unknown')
    req_logger = get_request_logger(request_id)

    req_logger.debug(f"Polling job status: {job_id}")

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