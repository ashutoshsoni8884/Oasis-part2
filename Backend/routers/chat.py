"""
Chat Router — POST /api/chat, GET /api/chat/{job_id}
Async pattern: POST returns job_id immediately, GET polls for result
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from Backend.models.chat import ChatRequest, ChatResponse, JobResponse, JobStatusResponse
from Backend.models.user import User
from Backend.services import intent_classifier
from Backend.services.agent_registry import get_agent_for_intent
from Backend.db import SessionLocal, PromptLog
from Backend.utils import job_manager
from Backend.utils.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=JobResponse)
async def chat_submit(request: ChatRequest, current_user: User = Depends(get_current_user)) -> JobResponse:
    """
    Submit a chat query for async processing.
    Returns job_id immediately. Use GET /api/chat/{job_id} to poll for results.
    
    Requires:
    - query: The user query

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

    # ── Step 1: Classify intent ─────────────────────────────────────────
    try:
        classification = await intent_classifier.classify(query, request.history)
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to classify query intent"
        )

    intent = classification["intent"]
    agent_id = classification["agent_id"]
    confidence = classification["confidence"]

    logger.info(f"Classified: intent={intent}, agent={agent_id}, confidence={confidence}")

    # ── Step 2: Handle unknown intent ───────────────────────────────────
    if intent == "UNKNOWN" or not agent_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not confidently match your query to an agent. "
                "Try mentioning invoices, project margins, payroll, procurement, or finance close."
            )
        )

    # ── Step 3: Verify agent exists ─────────────────────────────────────
    agent = get_agent_for_intent(intent)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"No agent configured for intent '{intent}'"
        )

    # ── Step 4: Create job and return job_id ────────────────────────────
    api_job_id = job_manager.create_job(
        query=query,
        bearer_token=request.bearer_token,
        owner_id=current_user.id,
    )
    
    # Store classification and agent info for later use
    job_manager.update_job(
        api_job_id, 
        status="QUEUED",
        result={
            "intent": intent,
            "agent_id": agent_id,
            "confidence": confidence,
        }
    )

    logger.info(f"Job created: {api_job_id}")

    # ── Step 5: Log to database ─────────────────────────────────────────
    db = SessionLocal()
    try:
        log_entry = PromptLog(
            query=query,
            endpoint="/api/chat",
            agent_id=agent_id,
            intent=intent,
            confidence=str(confidence),
        )
        db.add(log_entry)
        db.commit()
        logger.info("Prompt logged to database")
    except Exception as e:
        logger.error(f"Failed to log to database: {e}")
        db.rollback()
    finally:
        db.close()

    # ── Step 6: Invoke agent asynchronously (mock or Oracle Fusion) ─
    from Backend.config import get_settings

    settings = get_settings()

    if settings.MOCK_MODE:
        from Backend.services.mock_agent_service import get_mock_response

        response = await get_mock_response(agent_id, intent, confidence, query)
        job_manager.update_job(
            api_job_id,
            status="COMPLETE",
            result=response.dict() if hasattr(response, "dict") else response,
        )
    else:
        from Backend.services.oracle_agent_service import invoke_oracle_agent

        await invoke_oracle_agent(
            query=query,
            intent=intent,
            confidence=confidence,
            agent_id=agent_id,
            bearer_token=request.bearer_token,
            job_id=api_job_id,
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
    
    # If job is still processing, return status without result
    if status in ("QUEUED", "RUNNING"):
        return JobStatusResponse(
            job_id=job_id,
            status=status,
            message=f"Still processing... (status: {status})",
        )
    
    # If job is complete, return result
    if status == "COMPLETE":
        result = job_manager.get_result(job_id, owner_id=current_user.id)
        if result:
            return JobStatusResponse(
                job_id=job_id,
                status="COMPLETE",
                result=result if isinstance(result, ChatResponse) else ChatResponse(**result),
            )
    
    # If job has error, return error
    if status == "ERROR":
        error = job_manager.get_error(job_id, owner_id=current_user.id)
        return JobStatusResponse(
            job_id=job_id,
            status="ERROR",
            error=error or "Unknown error",
        )
    
    # Unknown status
    return JobStatusResponse(
        job_id=job_id,
        status=status,
        message="Job status unknown",
    )


# ── Commented out: Old synchronous endpoint ───────────────────────────────────
"""
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    # Process a user query:
    # 1. Classify intent with LLM (or regex fallback)
    # 2. Route to the appropriate agent
    # 3. Return structured response
    
    settings = get_settings()
    query = request.query.strip()

    if not query:
        return ChatResponse(
            success=False,
            fallback=True,
            message="Please enter a query.",
        )

    logger.info(f"Chat query: {query[:100]}")

    # ── Step 1: Classify intent ─────────────────────────────────────────
    classification = await intent_classifier.classify(query, request.history)

    intent = classification["intent"]
    agent_id = classification["agent_id"]
    confidence = classification["confidence"]

    logger.info(f"Classified: intent={intent}, agent={agent_id}, confidence={confidence}")

    # ── Step 2: Handle unknown intent ───────────────────────────────────
    if intent == "UNKNOWN" or not agent_id:
        return ChatResponse(
            success=False,
            fallback=True,
            message=(
                "I couldn't confidently match your query to an agent. "
                "Could you be more specific? Try mentioning invoices, project margins, "
                "payroll, procurement orders, or finance close."
            ),
        )

    # ── Step 3: Verify agent exists ─────────────────────────────────────
    agent = get_agent_for_intent(intent)
    if not agent:
        return ChatResponse(
            success=False,
            fallback=True,
            message=f"No agent configured for intent '{intent}'.",
        )

    # ── Step 4: Invoke agent (mock or real) ─────────────────────────────
    if settings.MOCK_MODE:
        from Backend.services.mock_agent_service import get_mock_response
        response = await get_mock_response(agent_id, intent, confidence, query)
    else:
        from Backend.services.oracle_agent_service import invoke_oracle_agent
        response = await invoke_oracle_agent(query, intent, confidence, agent_id, request.bearer_token, request.job_id)

    logger.info(f"Response: success={response.success}, agent={response.agent_id}")

    # ── Step 5: Log to database ─────────────────────────────────────────
    db = SessionLocal()
    try:
        log_entry = PromptLog(
            query=query,
            endpoint="/api/chat",
            agent_id=response.agent_id,
            intent=intent,
            confidence=str(confidence)
        )
        db.add(log_entry)
        db.commit()
        logger.info("Prompt logged to database")
    except Exception as e:
        logger.error(f"Failed to log to database: {e}")
        db.rollback()
    finally:
        db.close()

    return response
"""
