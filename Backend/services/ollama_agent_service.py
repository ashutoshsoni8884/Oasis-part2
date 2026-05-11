"""
Local Ollama service integration.
Implements async job update flow compatible with /api/chat polling.
"""

import asyncio
import logging
from typing import Any

import httpx

from Backend.config import get_settings
from Backend.models.chat import ChatResponse
from Backend.services.response_formatter import format_oracle_response
from Backend.utils import job_manager

logger = logging.getLogger(__name__)


async def invoke_ollama_agent(
    query: str,
    intent: str,
    confidence: float,
    agent_id: str,
    job_id: str,
    history: list[dict[str, Any]] | None = None,
) -> ChatResponse:
    """
    Queue an Ollama request in the background and return immediately.
    """
    job_manager.update_job(job_id, status="RUNNING")
    asyncio.create_task(
        _run_ollama_async(
            query=query,
            intent=intent,
            confidence=confidence,
            agent_id=agent_id,
            job_id=job_id,
            history=history,
        )
    )
    return ChatResponse(
        success=True,
        message="Job queued for local Ollama processing.",
    )


def _build_prompt(query: str, history: list[dict[str, Any]] | None = None) -> str:
    """
    Build a compact prompt with short conversation context.
    """
    if not history:
        return query

    chunks: list[str] = [
        (
            "You are an Oracle ERP assistant. Answer in concise business language. "
            "If possible, return useful numeric facts and keep formatting simple."
        )
    ]
    for item in history[-6:]:
        role = str(item.get("role", "user")).strip().lower()
        content = str(
            item.get("content")
            or item.get("text")
            or item.get("narrative")
            or ""
        ).strip()
        if not content:
            continue
        if role not in {"user", "assistant", "system"}:
            role = "user"
        chunks.append(f"{role}: {content}")

    chunks.append(f"user: {query}")
    return "\n".join(chunks)


async def _run_ollama_async(
    query: str,
    intent: str,
    confidence: float,
    agent_id: str,
    job_id: str,
    history: list[dict[str, Any]] | None = None,
) -> None:
    settings = get_settings()
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    prompt = _build_prompt(query, history)
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    logger.info(f"[{job_id}] Sending query to Ollama model '{settings.OLLAMA_MODEL}'")

    try:
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload)
    except httpx.RequestError as exc:
        logger.error(f"[{job_id}] Ollama request error: {exc}")
        job_manager.update_job(
            job_id,
            status="ERROR",
            error=f"Could not reach local Ollama at {settings.OLLAMA_BASE_URL}: {exc}",
        )
        return

    if resp.status_code != 200:
        logger.error(f"[{job_id}] Ollama failed: HTTP {resp.status_code} - {resp.text}")
        job_manager.update_job(
            job_id,
            status="ERROR",
            error=f"Ollama returned HTTP {resp.status_code}. Body: {resp.text}",
        )
        return

    try:
        data = resp.json()
    except Exception as exc:
        logger.error(f"[{job_id}] Invalid Ollama JSON response: {exc}")
        job_manager.update_job(
            job_id,
            status="ERROR",
            error="Ollama returned invalid JSON.",
        )
        return

    output_text = str(data.get("response", "")).strip()
    if not output_text:
        job_manager.update_job(
            job_id,
            status="ERROR",
            error="Ollama returned an empty response (no 'response' field).",
        )
        return

    formatted = format_oracle_response(
        oracle_output=output_text,
        intent=intent,
        confidence=confidence,
        agent_id=agent_id,
    )
    job_manager.update_job(
        job_id,
        status="COMPLETE",
        result=formatted.dict() if hasattr(formatted, "dict") else formatted,
    )
    logger.info(f"[{job_id}] Ollama response processed successfully")
