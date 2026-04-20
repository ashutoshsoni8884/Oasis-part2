"""
Chat Router — POST /api/chat
The single endpoint that orchestrates the full flow:
  prompt → classify → select agent → invoke → respond
"""

import logging
from fastapi import APIRouter

from config import get_settings
from models.chat import ChatRequest, ChatResponse
from services import intent_classifier
from services.agent_registry import get_agent_for_intent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a user query:
    1. Classify intent with LLM (or regex fallback)
    2. Route to the appropriate agent
    3. Return structured response
    """
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
        from services.mock_agent_service import get_mock_response
        response = await get_mock_response(agent_id, intent, confidence, query)
    else:
        from services.oracle_agent_service import invoke_oracle_agent
        response = await invoke_oracle_agent(query, intent, confidence, agent_id)

    logger.info(f"Response: success={response.success}, agent={response.agent_id}")
    return response
