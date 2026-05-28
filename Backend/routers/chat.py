"""
Chat Router — POST /api/chat, GET /api/chat/{job_id}
Async pattern: POST returns job_id immediately, GET polls for result
Uses Ollama + Database for intelligent agent routing
"""

import logging
from fastapi import APIRouter, HTTPException

from config import get_settings
from models.chat import ChatRequest, ChatResponse, JobResponse, JobStatusResponse
from services.ollama_router import route_to_agent
from services.oracle_agent_service import invoke_oracle_agent
from db import SessionLocal, PromptLog
from utils import job_manager
from services.ollama_router import end_workflow  # Import workflow manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=JobResponse)
async def chat_submit(request: ChatRequest) -> JobResponse:
    """
    Submit a chat query for async processing.
    Returns job_id immediately. Use GET /api/chat/{job_id} to poll for results.
    
    Requires:
    - query: The user query
    - bearer_token: Authentication token for Oracle Fusion (ONE token for ALL agents)
    
    Optional:
    - session_id: Session identifier
    - history: Conversation history
    """
    settings = get_settings()
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty"
        )
    
    if not request.bearer_token:
        raise HTTPException(
            status_code=401,
            detail="bearer_token is required for authentication"
        )

    logger.info(f"Chat query submitted: {query[:100]}")
    logger.info(f"Session ID: {request.session_id}")
    logger.info(f"History length: {len(request.history) if request.history else 0}")

    # ── STEP 1: Use Ollama + Database to route to correct agent ─────────────
    agent_code = None
    agent_name = None
    confidence = 1.0
    agent_version = None

    # Debug: Log history contents for troubleshooting
    if request.history:
        logger.info("=== Conversation History ===")
        for i, msg in enumerate(request.history[-4:]):  # Last 4 messages
            logger.info(f"  History[{i}]: role={msg.get('role')}, agent_id={msg.get('agent_id')}, agent_name={msg.get('agent_name')}, text={str(msg.get('text', ''))[:50]}")

    # Try to maintain sticky session from history (ENHANCED)
    if request.history:
        # First, try to get from last assistant message
        for msg in reversed(request.history):
            if msg.get("role") == "assistant" and msg.get("agent_id"):
                agent_code = msg.get("agent_id")
                agent_name = msg.get("agent_name", agent_code)
                logger.info(f"✅ Using sticky agent from assistant message: {agent_code}")
                break
        
        # If not found, try to get from last user message that has agent_id
        if not agent_code:
            for msg in reversed(request.history):
                if msg.get("role") == "user" and msg.get("agent_id"):
                    agent_code = msg.get("agent_id")
                    agent_name = msg.get("agent_name", agent_code)
                    logger.info(f"✅ Using sticky agent from user message: {agent_code}")
                    break
        
        # If still not found but query is short (likely a follow-up), check conversation context
        if not agent_code and len(query.split()) < 5:
            # Check if the conversation was with SUBSCRIPTIONCREATEAGENT
            for msg in request.history:
                if msg.get("agent_id") == "SUBSCRIPTIONCREATEAGENT":
                    agent_code = "SUBSCRIPTIONCREATEAGENT"
                    agent_name = "Subscription Creation Agent"
                    logger.info(f"✅ Using subscription agent based on conversation context")
                    break

    # If no sticky agent from history, route using Ollama
    if not agent_code:
        logger.info("No sticky agent found, calling route_to_agent...")
        try:
            # Pass session_id and conversation_history to router for context-aware routing
            routing_result = await route_to_agent(
                query, 
                session_id=request.session_id,
                conversation_history=request.history
            )
            logger.info(f"Routing result: {routing_result}")
        except Exception as e:
            logger.error(f"Ollama routing failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to route query: {str(e)}"
            )

        # Check if routing was successful
        if not routing_result.get("agent_code"):
            raise HTTPException(
                status_code=400,
                detail=f"Could not route your query. {routing_result.get('reasoning', 'Unknown reason')}. Please try rephrasing or ask about payments, subscriptions, or collections. Make sure the backend is running at http://localhost:8000 and you provided a valid bearer token."
            )

        agent_code = routing_result["agent_code"]
        agent_name = routing_result["agent_name"]
        confidence = routing_result["confidence"]
        agent_version = routing_result.get("version")

    logger.info(f"✅ FINAL ROUTING: agent_code={agent_code}, agent_name={agent_name}, version={agent_version}, confidence={confidence}")

    # ── STEP 2: Create job and return job_id ────────────────────────────────
    api_job_id = job_manager.create_job(
        query=query,
        bearer_token=request.bearer_token,
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
        session_id=request.session_id,
        agent_code=agent_code,  # Pass agent_code for workflow completion tracking
    )

    return JobResponse(
        job_id=api_job_id,
        status="QUEUED",
        message=f"Routed to {agent_name}. Poll with GET /api/chat/{api_job_id}",
    )


@router.get("/chat/{job_id}", response_model=JobStatusResponse)
async def chat_poll(job_id: str) -> JobStatusResponse:
    """
    Poll for the result of an async chat job.
    
    Returns:
    - status: "QUEUED" | "RUNNING" | "COMPLETE" | "ERROR"
    - result: ChatResponse (only when status == "COMPLETE")
    - error: Error message (only when status == "ERROR")
    """
    job_status = job_manager.get_job_status(job_id)
    
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
        result = job_manager.get_result(job_id)
        if result:
            # Get additional job info if needed for workflow cleanup
            from services.oracle_agent_service import get_job_state
            job_state = get_job_state(job_id)
            
            # If this was a subscription creation workflow that completed,
            # we might want to end the workflow here as an additional safety measure
            if job_state and job_state.get("agent_code") == "SUBSCRIPTIONCREATEAGENT":
                # Check if the result indicates completion
                if result.get("narrative"):
                    narrative = result.get("narrative", "").lower()
                    if any(phrase in narrative for phrase in ["subscription created successfully", "all done", "create another?"]):
                        logger.info(f"Workflow completion detected in poll, ending workflow for session {job_state.get('session_id')}")
                        # Note: The workflow is already ended in oracle_agent_service.py
                        # This is just an additional safety measure
            
            return JobStatusResponse(
                job_id=job_id,
                status="COMPLETE",
                result=result if isinstance(result, ChatResponse) else ChatResponse(**result),
            )
    
    if status == "ERROR":
        error = job_manager.get_error(job_id)
        # End workflow on error if it was a subscription workflow
        from services.oracle_agent_service import get_job_state
        job_state = get_job_state(job_id)
        if job_state and job_state.get("agent_code") == "SUBSCRIPTIONCREATEAGENT":
            if job_state.get("session_id"):
                logger.info(f"Ending workflow for session {job_state.get('session_id')} due to error")
                end_workflow(job_state.get("session_id"))
        
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


# ─── Additional endpoint to manually end a workflow (optional) ────────────────
@router.post("/chat/{session_id}/end_workflow")
async def end_session_workflow(session_id: str):
    """
    Manually end a workflow for a session.
    Useful if a user wants to start a new conversation context.
    """
    try:
        end_workflow(session_id)
        return {
            "success": True,
            "message": f"Workflow ended for session {session_id}"
        }
    except Exception as e:
        logger.error(f"Failed to end workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to end workflow: {str(e)}"
        )