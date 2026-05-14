# services/ollama_router.py
"""
Ollama Router - Fetches agents from database and routes queries
"""

import httpx
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# Cache configuration (reduce database calls)
_cache = {"agents": None, "expiry": None}
CACHE_TTL_SECONDS = 60  # Refresh every minute


async def fetch_agents_from_database() -> list:
    """
    Fetch all active agents from the database via internal API call.
    Uses caching to avoid database hits on every request.
    """
    global _cache
    
    # Return cached data if still fresh
    if _cache["agents"] and _cache["expiry"] and datetime.utcnow() < _cache["expiry"]:
        logger.debug(f"Using cached agents: {len(_cache['agents'])} agents")
        return _cache["agents"]
    
    # Fetch from database via internal API
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get("http://localhost:8000/api/agent-registry/list")
            response.raise_for_status()
            data = response.json()
            
            _cache["agents"] = data["agents"]
            _cache["expiry"] = datetime.utcnow() + timedelta(seconds=CACHE_TTL_SECONDS)
            
            logger.info(f"Fetched {len(_cache['agents'])} agents from database")
            return _cache["agents"]
            
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch agents from database: {e}")
            # Return cached data if available, even if expired
            if _cache["agents"]:
                logger.warning(f"Using stale cache with {len(_cache['agents'])} agents")
                return _cache["agents"]
            return []


def build_routing_prompt(user_query: str, agents: list) -> str:
    """
    Build the prompt for Ollama using database-stored agent descriptions.
    No hardcoded agents - everything comes from database.
    """
    
    if not agents:
        return "No agents available in database."
    
    # Build agent list from database records
    agent_list = "\n\n".join([
        f"""AGENT CODE: {agent['team_code']}
AGENT NAME: {agent['team_name']}
CAPABILITIES: {agent['description']}"""
        for agent in agents
    ])
    
    # Build the list of valid agent codes for validation
    valid_codes = [agent['team_code'] for agent in agents]
    
    return f"""You are an intelligent router for Oracle Fusion AI agents. Your ONLY job is to select which agent should handle the user's query.

AVAILABLE AGENTS:
{agent_list}

IMPORTANT RULES:
1. Read the user's query carefully
2. Select the agent whose CAPABILITIES best match what the user is asking
3. Respond with ONLY the AGENT CODE - nothing else, no explanation, no punctuation
4. Valid agent codes are: {', '.join(valid_codes)}
5. If NO agent matches, respond with "UNKNOWN"

EXAMPLES:
- "Show me payment history for account ACC12345" → ARCREDITAGENTTEAM
- "What's my credit limit?" → ARCREDITAGENTTEAM  
- "Summarize subscription CDRM_31195" → CX_OSS_SUBSCRIPTION_AUTHORING_TEAM_SPL
- "Show upcoming renewals" → CX_OSS_SUBSCRIPTION_AUTHORING_TEAM_SPL
- "Create a promise to pay" → AGENTTEAMSCOLLECTORBUDDY
- "Create a dispute for invoice" → AGENTTEAMSCOLLECTORBUDDY

Now respond with ONLY the Agent Code:

User Query: {user_query}

Agent Code:"""


async def route_to_agent(user_query: str) -> Dict[str, Any]:
    """
    Main routing function:
    1. Fetches all active agents from database
    2. Uses Ollama Llama 3.2 to select the correct agent
    3. Returns the selected agent code
    
    Returns:
        {
            "agent_code": "ARCREDITAGENTTEAM" or None,
            "agent_name": "Credit Management Agent" or None,
            "confidence": 0.95,
            "reasoning": "..."
        }
    """
    
    # Step 1: Get all agents from database
    agents = await fetch_agents_from_database()
    
    if not agents:
        logger.error("No agents found in database")
        return {
            "agent_code": None,
            "agent_name": None,
            "confidence": 0.0,
            "reasoning": "No agents registered in database. Please register agent teams via /api/agent-registry/register"
        }
    
    logger.info(f"Routing query with {len(agents)} available agents")
    
    # Step 2: Build prompt with database agents
    prompt = build_routing_prompt(user_query, agents)
    
    # Step 3: Call Ollama
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,  # Low temperature for consistent routing
                    "max_tokens": 50      # Enough for agent code
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama returned {response.status_code}: {response.text}")
                return {
                    "agent_code": None,
                    "agent_name": None,
                    "confidence": 0.0,
                    "reasoning": f"Ollama service error: HTTP {response.status_code}"
                }
            
            result = response.json()
            raw_response = result["response"]
            selected_code = raw_response.strip().upper()
            
            print(f"DEBUG: Ollama raw response: '{raw_response}'")
            logger.info(f"Ollama selected: {selected_code}")
            
            # Step 4: Validate the response against database agents
            valid_codes = [a["team_code"].upper() for a in agents]
            
            if selected_code in valid_codes:
                # Find the agent details
                agent = next((a for a in agents if a["team_code"].upper() == selected_code), None)
                return {
                    "agent_code": selected_code,
                    "agent_name": agent["team_name"] if agent else selected_code,
                    "confidence": 0.95,
                    "reasoning": f"Successfully routed to {selected_code}",
                    "version": agent.get("version") if agent else None
                }
            elif selected_code == "UNKNOWN":
                return {
                    "agent_code": None,
                    "agent_name": None,
                    "confidence": 0.0,
                    "reasoning": "Ollama determined no agent matches this query"
                }
            else:
                # Ollama returned something unexpected
                logger.warning(f"Ollama returned invalid code: {selected_code}. Valid codes: {valid_codes}")
                return {
                    "agent_code": None,
                    "agent_name": None,
                    "confidence": 0.0,
                    "reasoning": f"Invalid agent code returned: {selected_code}"
                }
                
    except httpx.ConnectError:
        logger.warning("Ollama not running. Using keyword-based fallback routing.")
        # Fallback to keyword matching
        selected_agent = None
        user_query_lower = user_query.lower()
        
        # Simple keyword rules
        if any(kw in user_query_lower for kw in ["payment", "credit", "receivable", "invoice", "history", "limit"]):
            selected_agent = next((a for a in agents if a["team_code"] == "ARCREDITAGENTTEAM"), None)
        elif any(kw in user_query_lower for kw in ["subscription", "renewal", "product", "lifecycle", "expiring", "billing"]):
            selected_agent = next((a for a in agents if a["team_code"] == "CX_OSS_SUBSCRIPTION_AUTHORING_TEAM_SPL"), None)
        elif any(kw in user_query_lower for kw in ["collection", "debt", "promise", "dispute", "arrangement"]):
            selected_agent = next((a for a in agents if a["team_code"] == "AGENTTEAMSCOLLECTORBUDDY"), None)
            
        if selected_agent:
            return {
                "agent_code": selected_agent["team_code"],
                "agent_name": selected_agent["team_name"],
                "confidence": 0.7,
                "reasoning": "Routed via keyword-based fallback (Ollama unavailable)",
                "version": selected_agent.get("version")
            }
        
        return {
            "agent_code": None,
            "agent_name": None,
            "confidence": 0.0,
            "reasoning": "Ollama service not available and no keywords matched. Please start Ollama with 'ollama serve'"
        }
    except Exception as e:
        logger.error(f"Ollama routing failed: {e}")
        return {
            "agent_code": None,
            "agent_name": None,
            "confidence": 0.0,
            "reasoning": f"Routing error: {str(e)}"
        }


# Optional: Function to clear cache (useful after new agent registration)
def clear_agent_cache():
    """Clear the cached agents list to force fresh database fetch"""
    global _cache
    _cache = {"agents": None, "expiry": None}
    logger.info("Agent cache cleared")