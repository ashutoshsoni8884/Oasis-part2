"""
Oracle Fusion AI Agent Studio Service.
Implements the async invoke-then-poll pattern:
  1. POST /invokeAsync → get jobId
  2. GET /status/{jobId} → poll until COMPLETE
"""

import asyncio
import logging
import httpx
from config import get_settings
from utils.oauth import get_oracle_token, get_basic_auth_header
from services.response_formatter import format_oracle_response
from models.chat import ChatResponse

logger = logging.getLogger(__name__)

MAX_POLL_ATTEMPTS = 30
POLL_INTERVAL_SECONDS = 2


async def invoke_oracle_agent(query: str, intent: str, confidence: float, agent_id: str) -> ChatResponse:
    """
    Call Oracle Fusion AI Agent Studio using the invokeAsync + poll pattern.
    """
    settings = get_settings()
    # Try to get OAuth token, fallback to Basic Auth if not configured/fails
    token = await get_oracle_token()
    
    # Clean up host (remove https:// if present)
    host = settings.FUSION_HOST.replace("https://", "").replace("http://", "").rstrip("/")
    base_url = f"https://{host}/api/fusion-ai/orchestrator/agent/v2/{settings.AGENT_TEAM_CODE}"

    if token:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    else:
        # Fallback to Basic Auth with user/pass
        basic_header = get_basic_auth_header()
        if not basic_header:
            return ChatResponse(
                success=False,
                fallback=True,
                message="Authentication not configured. Please provide either OAuth credentials or Fusion User ID/Password in the .env file.",
            )
        headers = {
            "Authorization": basic_header,
            "Content-Type": "application/json",
        }
        logger.info(f"Using Basic Auth header (user: {settings.FUSION_USER})")

    invoke_payload = {
        "conversational": "true",
        "version": settings.AGENT_TEAM_VERSION,
        "status": "PUBLISHED",
        "message": query,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        # ── Step 1: Invoke ──────────────────────────────────────────────
        logger.info(f"Invoking Oracle agent: {settings.AGENT_TEAM_CODE} with query: {query[:80]}...")

        try:
            invoke_response = await client.post(
                f"{base_url}/invokeAsync",
                json=invoke_payload,
                headers=headers,
            )
        except httpx.RequestError as e:
            logger.error(f"Failed to invoke Oracle agent: {e}")
            return ChatResponse(
                success=False,
                fallback=True,
                message=f"Could not reach Oracle Fusion: {str(e)}",
            )

        if invoke_response.status_code != 200:
            logger.error(f"Oracle invoke failed: {invoke_response.status_code} — {invoke_response.text}")
            logger.error(f"Response headers: {invoke_response.headers}")
            return ChatResponse(
                success=False,
                fallback=True,
                message=f"Oracle agent invocation failed (HTTP {invoke_response.status_code}). Please check your credentials and agent configuration.",
            )

        invoke_data = invoke_response.json()
        job_id = invoke_data.get("jobId")
        conversation_id = invoke_data.get("conversationId")

        if not job_id:
            logger.error(f"No jobId in invoke response: {invoke_data}")
            return ChatResponse(
                success=False,
                fallback=True,
                message="Oracle agent did not return a job ID.",
            )

        logger.info(f"Oracle job started: {job_id} (conversation: {conversation_id})")

        # ── Step 2: Poll for result ─────────────────────────────────────
        for attempt in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

            try:
                status_response = await client.get(
                    f"{base_url}/status/{job_id}",
                    headers=headers,
                )
            except httpx.RequestError as e:
                logger.warning(f"Poll attempt {attempt + 1} failed: {e}")
                continue

            if status_response.status_code != 200:
                logger.warning(f"Poll returned {status_response.status_code}")
                continue

            status_data = status_response.json()
            status = status_data.get("status", "").upper()

            logger.info(f"Poll {attempt + 1}/{MAX_POLL_ATTEMPTS}: status={status}")

            if status == "COMPLETE":
                # Parse and format the Oracle response
                oracle_output = status_data.get("output", "")
                return format_oracle_response(
                    oracle_output=oracle_output,
                    intent=intent,
                    confidence=confidence,
                    agent_id=agent_id,
                )

            elif status == "ERROR":
                error_msg = status_data.get("error", "Unknown error from Oracle agent")
                logger.error(f"Oracle agent error: {error_msg}")
                return ChatResponse(
                    success=False,
                    fallback=True,
                    message=f"Oracle agent returned an error: {error_msg}",
                )

            elif status in ("RUNNING", "WAITING"):
                continue
            else:
                logger.warning(f"Unknown status: {status}")
                continue

        # Timeout
        logger.error(f"Oracle agent timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s")
        return ChatResponse(
            success=False,
            fallback=True,
            message="Oracle agent took too long to respond. Please try again.",
        )
