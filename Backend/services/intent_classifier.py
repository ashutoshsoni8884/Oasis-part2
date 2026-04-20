"""
Intent Classifier — uses Google Gemini LLM to determine which Oracle agent
should handle a user's natural language query.

Falls back to regex pattern matching if the LLM is unavailable.
"""

import json
import re
import logging
from config import get_settings
from services.agent_registry import get_all_agents, get_agent_for_intent

logger = logging.getLogger(__name__)

# ─── Regex fallback patterns ───────────────────────────────────────────────────
INTENT_PATTERNS = [
    (r"invoice|unpaid|receivable|ar\b|credit|ageing|aging|siemens|dunning|overdue|outstanding", "AR_CREDIT_QUERY", 0.85),
    (r"aging report|ageing report|q[0-9]|quarter.*receiv", "AR_AGING_REPORT", 0.82),
    (r"margin|project.risk|ppm|at risk|margin risk", "PPM_MARGIN_RISK", 0.84),
    (r"revenue|forecast|actuals|ppm revenue", "PPM_REVENUE", 0.81),
    (r"close|month.end|period|delayed|journal|finance close", "FINANCE_CLOSE", 0.83),
    (r"purchase.order|po\s|procurement|vendor|supplier|open order", "PROCUREMENT_QUERY", 0.85),
    (r"leave|payroll|hcm|employee|team|headcount|salary|attendance", "HCM_LEAVE", 0.80),
]


def _build_system_prompt() -> str:
    """Build the system prompt that teaches the LLM about available agents."""
    agents = get_all_agents()
    agent_descriptions = []
    for a in agents:
        intents = ", ".join(a.intents)
        agent_descriptions.append(
            f"- Agent: {a.name} (id: {a.id})\n"
            f"  Intents: [{intents}]\n"
            f"  Handles: {a.description}"
        )
    agents_block = "\n".join(agent_descriptions)

    return f"""You are an intent classifier for Oracle Fusion Cloud ERP.
Given a user query, determine which AI agent should handle it.

Available agents and their intents:
{agents_block}

Respond ONLY with valid JSON (no markdown, no code fences):
{{
  "intent": "<INTENT_CODE>",
  "agent_id": "<agent_id>",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation>"
}}

If no agent matches, respond with:
{{
  "intent": "UNKNOWN",
  "agent_id": null,
  "confidence": 0.0,
  "reasoning": "No matching agent found"
}}"""


async def classify_with_llm(query: str, history: list[dict] | None = None) -> dict:
    """Classify intent using Google Gemini."""
    settings = get_settings()

    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your-gemini-api-key-here":
        logger.warning("Gemini API key not configured — falling back to regex")
        return classify_with_regex(query)

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        system_prompt = _build_system_prompt()

        # Build context from history if available
        context = ""
        if history:
            recent = history[-4:]  # Last 4 messages for context
            context = "\n\nRecent conversation:\n" + "\n".join(
                f"{'User' if m.get('role') == 'user' else 'Agent'}: {m.get('text', m.get('narrative', ''))}"
                for m in recent if m.get('text') or m.get('narrative')
            )

        prompt = f"{system_prompt}{context}\n\nUser query: {query}"

        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)

        result = json.loads(raw_text)

        # Validate the response
        intent = result.get("intent", "UNKNOWN")
        agent_id = result.get("agent_id")
        confidence = float(result.get("confidence", 0.0))

        # Verify agent exists
        if intent != "UNKNOWN" and agent_id:
            agent = get_agent_for_intent(intent)
            if agent is None:
                logger.warning(f"LLM returned unknown intent '{intent}', falling back to regex")
                return classify_with_regex(query)

        return {
            "intent": intent,
            "agent_id": agent_id,
            "confidence": min(confidence, 1.0),
            "reasoning": result.get("reasoning", ""),
        }

    except Exception as e:
        logger.error(f"Gemini classification failed: {e}")
        return classify_with_regex(query)


def classify_with_regex(query: str) -> dict:
    """Fallback intent classification using regex patterns."""
    query_lower = query.lower()

    for pattern, intent, conf in INTENT_PATTERNS:
        if re.search(pattern, query_lower):
            agent = get_agent_for_intent(intent)
            return {
                "intent": intent,
                "agent_id": agent.id if agent else None,
                "confidence": conf,
                "reasoning": f"Matched regex pattern for {intent}",
            }

    return {
        "intent": "UNKNOWN",
        "agent_id": None,
        "confidence": 0.0,
        "reasoning": "No matching pattern found",
    }


async def classify(query: str, history: list[dict] | None = None) -> dict:
    """Main entry point — tries LLM first, falls back to regex."""
    return await classify_with_llm(query, history)
