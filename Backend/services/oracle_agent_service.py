"""
Oracle Fusion AI Agent Studio Service.
Implements the async invoke-then-poll pattern:
  1. POST /invokeAsync → get jobId
  2. GET /status/{jobId} → poll until COMPLETE
"""

import asyncio
import logging
import httpx
from Backend.config import get_settings
from Backend.utils.oauth import get_oracle_token, get_basic_auth_header
from Backend.services.response_formatter import format_oracle_response
from Backend.models.chat import ChatResponse
from Backend.utils import job_manager

logger = logging.getLogger(__name__)

MAX_POLL_ATTEMPTS = 300  # 300 * 1 second = 5 minutes
POLL_INTERVAL_SECONDS = 1
REQUEST_TIMEOUT = 60.0

# Mapping of api_job_id -> {oracle_job_id, headers, intent, confidence, agent_id}
_job_state = {}


async def invoke_oracle_agent(query: str, intent: str, confidence: float, agent_id: str, bearer_token: str = None, job_id: str = None) -> ChatResponse:
    """
    Call Oracle Fusion AI Agent Studio using the invokeAsync + poll pattern.
    For the new async flow:
    1. Quickly invokes the Oracle agent (returns oracle_job_id)
    2. Starts a background polling task
    3. Returns immediately
    
    Args:
        query: User query
        intent: Classified intent
        confidence: Classification confidence
        agent_id: Target agent ID
        bearer_token: Authentication token (required)
        job_id: API job_id (from job_manager)
    """
    settings = get_settings()
    
    # Construct base URL from settings
    host = settings.FUSION_HOST.replace('https://', '').replace('http://', '').rstrip('/')
    base_url = f"https://{host}/api/fusion-ai/orchestrator/agent/v2/{settings.AGENT_TEAM_CODE}"
    
    # Use provided bearer token if available, otherwise try OAuth, then Basic Auth
    if bearer_token:
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        }
        logger.info(f"[{job_id}] Using provided bearer token for authentication")
    else:
        token = await get_oracle_token()
        
        if token:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            logger.info(f"[{job_id}] Using OAuth token for authentication")
        else:
            # Fallback to Basic Auth with user/pass
            basic_header = get_basic_auth_header()
            if not basic_header:
                job_manager.update_job(
                    job_id,
                    status="ERROR",
                    error="Authentication not configured. Please provide either OAuth credentials, a bearer token, or Fusion User ID/Password in the .env file."
                )
                return ChatResponse(
                    success=False,
                    fallback=True,
                    message="Authentication not configured.",
                )
            headers = {
                "Authorization": basic_header,
                "Content-Type": "application/json",
            }
            logger.info(f"[{job_id}] Using Basic Auth header (user: {settings.FUSION_USER})")

    invoke_payload = {
        "message": query,
        "conversational": True,
        "invocationMode": "END_USER",
        # "version": settings.AGENT_TEAM_VERSION, # Omit version to use latest PUBLISHED
        "status": "PUBLISHED",
        "parameters": {},
        "conversationId": None,
        "useInternalConfig": False,  # Changed to False as it was working previously
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        # ── Step 1: Invoke ──────────────────────────────────────────────
        logger.info(f"[{job_id}] Invoking Oracle agent: {settings.AGENT_TEAM_CODE} with query: {query[:80]}...")

        try:
            logger.info(f"[{job_id}] HITTING URL EXACTLY: '{base_url}/invokeAsync'")
            invoke_response = await client.post(
                f"{base_url}/invokeAsync",
                json=invoke_payload,
                headers=headers,
            )
        except httpx.RequestError as e:
            logger.error(f"[{job_id}] Failed to invoke Oracle agent: {e}")
            job_manager.update_job(
                job_id,
                status="ERROR",
                error=f"Could not reach Oracle Fusion: {str(e)}"
            )
            return ChatResponse(
                success=False,
                fallback=True,
                message=f"Could not reach Oracle Fusion: {str(e)}",
            )

        if invoke_response.status_code not in (200, 202):
            logger.error(f"[{job_id}] Oracle invoke failed: {invoke_response.status_code} — {invoke_response.text}")
            logger.error(f"[{job_id}] Response headers: {invoke_response.headers}")
            job_manager.update_job(
                job_id,
                status="ERROR",
                error=f"Oracle agent invocation failed (HTTP {invoke_response.status_code})"
            )
            return ChatResponse(
                success=False,
                fallback=True,
                message=f"Oracle agent invocation failed (HTTP {invoke_response.status_code}).",
            )

        try:
            invoke_data = invoke_response.json()
        except Exception as e:
            logger.error(f"[{job_id}] Failed to parse invoke response: {e}")
            job_manager.update_job(
                job_id,
                status="ERROR",
                error=f"Failed to parse Oracle response: {str(e)}"
            )
            return ChatResponse(
                success=False,
                fallback=True,
                message="Failed to parse Oracle response.",
            )

        # DEBUG: Log full invoke response
        import json as _json
        logger.info(f"[{job_id}] ===== INVOKE RESPONSE (HTTP {invoke_response.status_code}) =====")
        logger.info(f"[{job_id}] {_json.dumps(invoke_data, indent=2, default=str)}")
        try:
            with open("debug_invoke_response.json", "w") as _f:
                _json.dump(invoke_data, _f, indent=2, default=str)
        except Exception:
            pass

        oracle_job_id = invoke_data.get("jobId")
        conversation_id = invoke_data.get("conversationId")

        if not oracle_job_id:
            logger.error(f"[{job_id}] No jobId in invoke response: {invoke_data}")
            job_manager.update_job(
                job_id,
                status="ERROR",
                error="Oracle agent did not return a job ID"
            )
            return ChatResponse(
                success=False,
                fallback=True,
                message="Oracle agent did not return a job ID.",
            )

        logger.info(f"[{job_id}] Oracle job started: {oracle_job_id} (conversation: {conversation_id})")

        # ── Step 2: Store job state and start background polling ───────
        _job_state[job_id] = {
            "oracle_job_id": oracle_job_id,
            "headers": headers,
            "base_url": base_url,
            "intent": intent,
            "confidence": confidence,
            "agent_id": agent_id,
        }
        
        # Update job status to RUNNING
        job_manager.update_job(job_id, status="RUNNING")
        
        # Start background polling task
        asyncio.create_task(
            _poll_oracle_async(
                api_job_id=job_id,
                oracle_job_id=oracle_job_id,
                base_url=base_url,
                headers=headers,
                intent=intent,
                confidence=confidence,
                agent_id=agent_id,
            )
        )
        
        logger.info(f"[{job_id}] Background polling started for Oracle job {oracle_job_id}")
        
        return ChatResponse(
            success=True,
            message=f"Job queued. Oracle job ID: {oracle_job_id}",
        )


async def _poll_oracle_async(
    api_job_id: str,
    oracle_job_id: str,
    base_url: str,
    headers: dict,
    intent: str,
    confidence: float,
    agent_id: str,
) -> None:
    """
    Background task: Poll Oracle Fusion for job completion.
    Updates job_manager with status and results.
    
    Args:
        api_job_id: The job_id returned to the client
        oracle_job_id: The Oracle Fusion job ID
        base_url: Oracle API base URL
        headers: Request headers with auth
        intent: Classified intent
        confidence: Classification confidence
        agent_id: Agent ID
    """
    logger.info(f"[{api_job_id}] Starting background polling for Oracle job {oracle_job_id}")
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for attempt in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

            try:
                status_response = await client.get(
                    f"{base_url}/status/{oracle_job_id}",
                    headers=headers,
                )
            except httpx.RequestError as e:
                logger.warning(f"[{api_job_id}] Poll attempt {attempt + 1} failed: {e}")
                continue

            if status_response.status_code != 200:
                logger.warning(f"[{api_job_id}] Poll returned {status_response.status_code}")
                continue

            try:
                status_data = status_response.json()
            except Exception as e:
                logger.warning(f"[{api_job_id}] Failed to parse poll response: {e}")
                continue

            # DEBUG: Log full poll response
            import json as _json
            logger.info(f"[{api_job_id}] ===== POLL RESPONSE (HTTP {status_response.status_code}) =====")
            logger.info(f"[{api_job_id}] {_json.dumps(status_data, indent=2, default=str)}")
            try:
                with open("debug_poll_response.json", "w") as _f:
                    _json.dump(status_data, _f, indent=2, default=str)
            except Exception:
                pass
                
            status = status_data.get("status", "").upper()

            logger.info(f"[{api_job_id}] Poll {attempt + 1}/{MAX_POLL_ATTEMPTS}: status={status}")

            if status == "COMPLETE":
                # Parse and format the Oracle response
                oracle_output = status_data.get("output", "")
                result = format_oracle_response(
                    oracle_output=oracle_output,
                    intent=intent,
                    confidence=confidence,
                    agent_id=agent_id,
                )
                
                # Update job_manager with result
                job_manager.update_job(
                    api_job_id,
                    status="COMPLETE",
                    result=result.dict() if hasattr(result, 'dict') else result,
                )
                
                logger.info(f"[{api_job_id}] Oracle job {oracle_job_id} completed successfully")
                return

            elif status == "ERROR":
                raw_error = status_data.get("error", "")
                oracle_output = status_data.get("output", "")
                logger.error(f"[{api_job_id}] Oracle agent error: {raw_error}")
                logger.error(f"[{api_job_id}] Oracle error full status_data: {status_data}")
                
                # If there's partial output despite the error, try to use it
                if oracle_output:
                    logger.info(f"[{api_job_id}] Oracle agent returned partial output despite error")
                    result = format_oracle_response(
                        oracle_output=oracle_output,
                        intent=intent,
                        confidence=confidence,
                        agent_id=agent_id,
                    )
                    job_manager.update_job(
                        api_job_id,
                        status="COMPLETE",
                        result=result.dict() if hasattr(result, 'dict') else result,
                    )
                    return
                
                # Build a user-friendly error message
                if "404" in str(raw_error):
                    friendly_error = (
                        f"The Oracle agent could not find the requested data. "
                        f"The resource or customer ID may not exist in Oracle Fusion. "
                        f"(Details: {raw_error})"
                    )
                elif "401" in str(raw_error) or "403" in str(raw_error):
                    friendly_error = (
                        f"Authentication failed with Oracle Fusion. "
                        f"Please check your bearer token. (Details: {raw_error})"
                    )
                else:
                    friendly_error = f"Oracle agent error: {raw_error or 'Unknown error'}"
                
                job_manager.update_job(
                    api_job_id,
                    status="ERROR",
                    error=friendly_error,
                )
                return

            elif status in ("RUNNING", "WAITING"):
                continue
            else:
                logger.warning(f"[{api_job_id}] Unknown status: {status}")
                continue

        # Timeout
        logger.error(f"[{api_job_id}] Oracle agent timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s")
        job_manager.update_job(
            api_job_id,
            status="ERROR",
            error=f"Oracle agent timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds"
        )
