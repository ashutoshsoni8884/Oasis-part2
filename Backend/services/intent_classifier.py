"""
Intent Classifier — selects the Oracle AI Agent Studio team using Ollama.

This module routes user queries to the correct agent team code by
fetching active agents from the database and asking Ollama to choose.
"""

import logging
from services.ollama_router import route_to_agent

logger = logging.getLogger(__name__)


async def classify_intent(message: str) -> dict:
    """
    Classify the user's message and return a routing payload.
    """
    route = await route_to_agent(message)

    return {
        "agent_team_code": route.get("agent_code"),
        "agent_name": route.get("agent_name"),
        "confidence": float(route.get("confidence", 0.0) or 0.0),
        "reasoning": route.get("reasoning", ""),
        "version": route.get("version"),
    }

