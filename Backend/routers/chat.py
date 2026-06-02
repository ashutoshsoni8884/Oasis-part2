"""
Chat Router — POST /api/chat (submit) + GET /api/chat/{job_id} (poll)

FIX SUMMARY:
  1. Removed broken PRIORITY 1/2 sticky-agent logic that read agent_id from
     history messages. Those messages store short display ids like "ar" not
     Oracle team codes like "ARCREDITAGENTTEAM" — the lookup always failed, and
     when it "worked" for SUBSCRIPTIONCREATEAGENT it passed NO conversation_id,
     restarting the Oracle flow from scratch on every turn.

  2. conversation_id=request.conversation_id is now correctly passed to
     invoke_oracle_agent so Oracle can resume the supervisor dialogue.

  3. get_conversation_id() is now imported and used correctly in the poll
     endpoint (the old import was crashing silently — function didn't exist).

  4. Oracle's real conversationId is returned in JobResponse immediately
     (at QUEUED status) so the frontend can store it before polling.
"""

import logging
from fastapi import APIRouter, HTTPException

from config import get_settings
from models.chat import ChatRequest, ChatResponse, JobResponse, JobStatusResponse
from services.ollama_router import route_to_agent, end_workflow
from services.oracle_agent_service import (
    invoke_oracle_agent,
    get_job_state,
    get_conversation_id,
)
from db import SessionLocal, PromptLog
from utils import job_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=JobResponse)
async def chat_submit(request: ChatRequest) -> JobResponse:
    """
    Submit a chat query for async processing.
    Returns job_id immediately. Poll GET /api/chat/{job_id} for results.

    Required: query, bearer_token
    Optional: session_id, history, conversation_id (Oracle's UUID from last response)

    IMPORTANT: Send back the conversation_id you received in the previous response
    on every subsequent turn. This is Oracle's own UUID — NOT your session_id.
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if not request.bearer_token:
        raise HTTPException(status_code=401, detail="bearer_token is required")

    logger.info(f"Chat query: {query[:100]}")
    logger.info(f"Session: {request.session_id} | Oracle conversationId: {request.conversation_id}")
    logger.info(f"History: {len(request.history or [])} msgs")

    if request.history:
        logger.info("=== History (last 4) ===")
        for i, msg in enumerate(request.history[-4:]):
            logger.info(
                f"  [{i}] role={msg.get('role')} | agent_id={msg.get('agent_id')} | "
                f"text={str(msg.get('text') or msg.get('narrative', ''))[:50]}"
            )

    # ── Route via Ollama + session workflow awareness ────────────────────────
    # route_to_agent handles all priority logic:
    #   P1 - active session workflow (highest — catches mid-flow subscription turns)
    #   P2 - subscription follow-up pattern match (bare number, date, yes/no)
    #   P3 - new subscription creation keyword
    #   P4 - Ollama LLM routing
    #   P5 - keyword fallback when Ollama is down
    try:
        routing_result = await route_to_agent(
            user_query=query,
            session_id=request.session_id,
            conversation_history=request.history,
            current_conversation_id=request.conversation_id,
        )
        logger.info(f"Routing: {routing_result}")
    except Exception as e:
        logger.error(f"Routing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to route query: {str(e)}")

    agent_code = routing_result.get("agent_code")
    agent_name = routing_result.get("agent_name")
    confidence = routing_result.get("confidence", 1.0)
    agent_version = routing_result.get("version")

    if not agent_code:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Could not route your query. "
                f"{routing_result.get('reasoning', 'No agent matched.')} "
                f"Please try rephrasing."
            ),
        )

    logger.info(
        f"ROUTING: agent={agent_code} | name={agent_name} | "
        f"version={agent_version} | confidence={confidence}"
    )

    # ── Create job ────────────────────────────────────────────────────────────
    api_job_id = job_manager.create_job(query=query, bearer_token=request.bearer_token)
    logger.info(f"Job created: {api_job_id}")

    # ── Log to database ───────────────────────────────────────────────────────
    db = SessionLocal()
    try:
        db.add(PromptLog(
            query=query, endpoint="/api/chat",
            agent_id=agent_code, intent=agent_name, confidence=str(confidence),
        ))
        db.commit()
    except Exception as e:
        logger.error(f"DB log failed: {e}")
        db.rollback()
    finally:
        db.close()

    # ── Invoke Oracle agent ───────────────────────────────────────────────────
    # Pass request.conversation_id (Oracle's UUID or None on first turn).
    # NEVER pass session_id here — Oracle rejects it with "workflow not found".
    invoke_result = await invoke_oracle_agent(
        query=query,
        intent=agent_name,
        confidence=confidence,
        agent_id=agent_code,
        bearer_token=request.bearer_token,
        job_id=api_job_id,
        version=agent_version,
        session_id=request.session_id,
        agent_code=agent_code,
        conversation_id=request.conversation_id,   # Oracle UUID or None (first turn)
    )

    # ── Return Oracle's conversationId immediately ────────────────────────────
    # The frontend must store this and send it back on the next request.
    new_conversation_id = None
    if invoke_result and hasattr(invoke_result, "conversation_id"):
        new_conversation_id = invoke_result.conversation_id
        if new_conversation_id:
            logger.info(f"Oracle conversationId to return: {new_conversation_id}")
        else:
            logger.warning("invoke_oracle_agent returned no conversationId")

    return JobResponse(
        job_id=api_job_id,
        status="QUEUED",
        message=f"Routed to {agent_name}. Poll GET /api/chat/{api_job_id}",
        conversation_id=new_conversation_id,   # Oracle's real UUID — frontend must store this
    )


@router.get("/chat/{job_id}", response_model=JobStatusResponse)
async def chat_poll(job_id: str) -> JobStatusResponse:
    """Poll for the result of a submitted job."""
    job_status = job_manager.get_job_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or expired")

    status = job_status["status"]
    conv_id = get_conversation_id(job_id)   # Oracle's UUID for this job

    if status in ("QUEUED", "RUNNING"):
        return JobStatusResponse(
            job_id=job_id, status=status,
            message=f"Processing... (status: {status})",
            conversation_id=conv_id,
        )

    if status == "COMPLETE":
        result_data = job_manager.get_result(job_id)
        if not result_data:
            raise HTTPException(status_code=500, detail="Job COMPLETE but result missing")

        chat_result = ChatResponse(**result_data) if not isinstance(result_data, ChatResponse) else result_data

        if conv_id and not chat_result.conversation_id:
            chat_result.conversation_id = conv_id

        return JobStatusResponse(
            job_id=job_id, status="COMPLETE",
            result=chat_result,
            conversation_id=chat_result.conversation_id or conv_id,
        )

    if status == "ERROR":
        error_msg = job_manager.get_error(job_id)
        job_state = get_job_state(job_id)
        if job_state and job_state.get("session_id"):
            logger.info(f"Ending workflow for session {job_state['session_id']} after ERROR")
            try:
                end_workflow(job_state["session_id"])
            except Exception as e:
                logger.warning(f"Could not end workflow: {e}")
        return JobStatusResponse(job_id=job_id, status="ERROR", error=error_msg or "Unknown error")

    return JobStatusResponse(job_id=job_id, status=status)


@router.post("/chat/{session_id}/end_workflow")
async def end_session_workflow(session_id: str):
    """Manually end a workflow so the user can start fresh."""
    try:
        end_workflow(session_id)
        return {"success": True, "message": f"Workflow ended for session {session_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end workflow: {str(e)}")