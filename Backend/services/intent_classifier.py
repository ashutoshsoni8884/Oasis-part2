"""
Intent Classifier — selects the Oracle AI Agent Studio team using Gemini.

This module uses Google Gemini to classify user intents and route to the
appropriate agent_team_code based on the query content.
"""

import logging
import google.generativeai as genai
from config import settings

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)


async def classify_intent(message: str) -> str:
    """
    Classify the user's message using Gemini and return the agent_team_code.

    Uses a simple prompt to route to available agents.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Analyze this user query and determine the most appropriate Oracle Fusion agent team code.
        Available teams: ARCREDITAGENTTEAM (for credit analysis), or other teams as needed.

        Query: {message}

        Return only the agent team code (e.g., ARCREDITAGENTTEAM).
        """
        response = model.generate_content(prompt)
        agent_team_code = response.text.strip()

        logger.info(f"Gemini classified '{message}' as agent_team_code: {agent_team_code}")
        return agent_team_code

    except Exception as e:
        logger.error(f"Gemini classification failed: {e}")
        # Fallback to default
        return "ARCREDITAGENTTEAM"

