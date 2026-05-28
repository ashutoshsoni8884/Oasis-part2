# services/ollama_router.py
"""
Ollama Router - Fetches agents from database and routes queries
with session awareness and workflow detection
"""

import httpx
import asyncio
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# Cache configuration (reduce database calls)
_cache = {"agents": None, "expiry": None}
CACHE_TTL_SECONDS = 5  # Refresh every 5 seconds for more responsive routing

# Active workflows storage: {session_id: {"agent_code": str, "step": str, "expires_at": datetime, "message_count": int}}
_active_workflows: Dict[str, Dict] = {}
WORKFLOW_TIMEOUT_SECONDS = 1800  # 30 minutes - enough for subscription creation flow

# Product names for subscription creation (for fast detection)
PRODUCT_NAMES = [
    "subscription_test_sku", "usage test", "test-02", "cars", "sample product",
    "test_subscription_product", "fees", "monthly fee", "air voice item",
    "test-03", "test-04", "test-12", "test-13", "test - 13"
]

# Currency codes
CURRENCIES = ["inr", "usd", "eur", "gbp", "jpy", "cad", "aud"]

# Action responses for subscription workflow
ACTIONS = ["yes", "no", "activate", "hold", "suspend", "cancel", "close", "hold product"]


# ============================================================================
# Session/Workflow Management Functions
# ============================================================================

def start_workflow(session_id: str, agent_code: str, step: str = "start") -> None:
    """Start a new workflow for a session"""
    if not session_id:
        return
    
    _active_workflows[session_id] = {
        "agent_code": agent_code,
        "step": step,
        "started_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(seconds=WORKFLOW_TIMEOUT_SECONDS),
        "message_count": 1
    }
    logger.info(f"Started workflow: session={session_id}, agent={agent_code}, step={step}")


def continue_workflow(session_id: str, step: str = None) -> Optional[str]:
    """Update an existing workflow and return the active agent code"""
    if not session_id or session_id not in _active_workflows:
        return None
    
    workflow = _active_workflows[session_id]
    
    # Check if expired
    if datetime.utcnow() > workflow["expires_at"]:
        del _active_workflows[session_id]
        logger.info(f"Workflow expired: session={session_id}")
        return None
    
    if step:
        workflow["step"] = step
    workflow["message_count"] += 1
    workflow["expires_at"] = datetime.utcnow() + timedelta(seconds=WORKFLOW_TIMEOUT_SECONDS)
    
    logger.info(f"Continued workflow: session={session_id}, agent={workflow['agent_code']}, step={workflow['step']}")
    return workflow["agent_code"]


def get_active_agent(session_id: str) -> Optional[str]:
    """Get the currently active agent for a session"""
    if not session_id or session_id not in _active_workflows:
        return None
    
    workflow = _active_workflows[session_id]
    if datetime.utcnow() > workflow["expires_at"]:
        del _active_workflows[session_id]
        return None
    
    return workflow["agent_code"]


def end_workflow(session_id: str) -> None:
    """End a workflow (call after completion or cancellation)"""
    if session_id and session_id in _active_workflows:
        agent = _active_workflows[session_id]["agent_code"]
        del _active_workflows[session_id]
        logger.info(f"Ended workflow: session={session_id}, agent={agent}")


def cleanup_expired_workflows() -> int:
    """Clean up expired workflows - call periodically"""
    now = datetime.utcnow()
    expired = [sid for sid, w in _active_workflows.items() if now > w["expires_at"]]
    for sid in expired:
        del _active_workflows[sid]
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired workflows")
    return len(expired)


# ============================================================================
# Helper Functions for Workflow Step Detection
# ============================================================================

def detect_workflow_step(user_query: str, conversation_history: List[dict] = None) -> str:
    """Detect which step of subscription creation we're at"""
    query_lower = user_query.lower().strip()
    
    # Check for product selection (number or product name)
    if re.match(r'^\d+$', user_query):
        return "product_selection"
    
    for product in PRODUCT_NAMES:
        if product.lower() in query_lower:
            return "product_selection"
    
    # Check for date selection
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if re.match(date_pattern, user_query):
        return "date_selection"
    
    if query_lower in ["today", "tomorrow", "default", "same"]:
        return "date_selection"
    
    # Check for currency selection
    if query_lower in CURRENCIES:
        return "currency_selection"
    
    # Check for activation/actions
    if query_lower in ["yes", "no", "activate"]:
        return "activation"
    
    if query_lower in ["hold", "hold product", "suspend", "cancel", "close"]:
        return "post_creation_action"
    
    return "in_progress"


def is_subscription_creation_request(query: str) -> bool:
    """Check if this is a NEW subscription creation request"""
    query_lower = query.lower()
    create_keywords = [
        'create subscription', 'provision subscription', 'new subscription',
        'set up subscription', 'add subscription', 'create a subscription',
        'enroll subscription', 'i need a subscription', 'start subscription'
    ]
    return any(kw in query_lower for kw in create_keywords)


def is_subscription_followup(user_query: str, conversation_history: List[dict] = None) -> bool:
    """Check if this looks like a subscription creation follow-up response"""
    query_lower = user_query.lower().strip()
    
    # Number (product selection)
    if re.match(r'^\d+$', user_query):
        return True
    
    # Product name
    for product in PRODUCT_NAMES:
        if product.lower() in query_lower:
            return True
    
    # Date format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', user_query):
        return True
    
    # Date keywords
    if query_lower in ["today", "tomorrow", "default", "same"]:
        return True
    
    # Currency
    if query_lower in CURRENCIES:
        return True
    
    # Action responses
    if query_lower in ACTIONS:
        return True
    
    # Check conversation history for recent subscription creation context
    if conversation_history:
        for msg in reversed(conversation_history[-4:]):
            if msg.get("role") == "assistant" and "SUBSCRIPTIONCREATEAGENT" in str(msg.get("agent_id", "")):
                return True
            # Check if assistant message contains product list
            if msg.get("role") == "assistant" and any(keyword in str(msg.get("text", "")).lower() for keyword in ["available products", "which product", "subscription", "start date", "end date"]):
                return True
    
    return False


# ============================================================================
# Main Database Fetch Function
# ============================================================================

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


# ============================================================================
# Prompt Building
# ============================================================================

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

IMPORTANT ROUTING RULES:
1. SUBSCRIPTION CREATION queries → SUBSCRIPTIONCREATEAGENT (CRITICAL: If the user says CREATE, PROVISION, SET UP, ADD, or ENROLL a subscription, especially "create subscription for [Company]", you MUST select SUBSCRIPTIONCREATEAGENT)
2. SUBSCRIPTION VIEWING queries → CX_OSS_SUBSCRIPTION_AUTHORING_TEAM_SPL (when user asks to VIEW, CHECK, LIST, or SUMMARIZE existing subscriptions)
3. PAYMENT/CREDIT queries → ARCREDITAGENTTEAM (when user asks about payment history, invoices, credit limits)
4. COLLECTIONS queries → AGENTTEAMSCOLLECTORBUDDY (when user needs to CREATE dispute, promise to pay, collection action)
5. Read the user's query carefully and match the ACTION word (CREATE=SUBSCRIPTIONCREATEAGENT, VIEW=CX_OSS_SUBSCRIPTION_AUTHORING_TEAM_SPL, PAY=ARCREDITAGENTTEAM)
6. Respond with ONLY the AGENT CODE - nothing else, no explanation, no punctuation
7. Valid agent codes are: {', '.join(valid_codes)}
8. If NO agent matches, respond with "UNKNOWN"

CRITICAL DISTINCTION:
- "Create subscription for XYZ" → SUBSCRIPTIONCREATEAGENT (NEW provisioning)
- "Show me subscription CDRM_31195" → CX_OSS_SUBSCRIPTION_AUTHORING_TEAM_SPL (EXISTING subscription query)
- "What is my credit limit" → ARCREDITAGENTTEAM (payment/credit info)

EXAMPLES:
- "Show me payment history for account ACC12345" → ARCREDITAGENTTEAM
- "What's my credit limit?" → ARCREDITAGENTTEAM  
- "Summarize subscription CDRM_31195" → CX_OSS_SUBSCRIPTION_AUTHORING_TEAM_SPL
- "Show upcoming renewals" → CX_OSS_SUBSCRIPTION_AUTHORING_TEAM_SPL
- "Create subscription for XYZ Limited" → SUBSCRIPTIONCREATEAGENT
- "Create subscription for ABC Consulting" → SUBSCRIPTIONCREATEAGENT
- "Set up a new subscription" → SUBSCRIPTIONCREATEAGENT
- "I need to create a subscription" → SUBSCRIPTIONCREATEAGENT
- "Provision new product for customer" → SUBSCRIPTIONCREATEAGENT
- "Create a promise to pay" → AGENTTEAMSCOLLECTORBUDDY
- "Create a dispute for invoice" → AGENTTEAMSCOLLECTORBUDDY

Now respond with ONLY the Agent Code:

User Query: {user_query}

Agent Code:"""


# ============================================================================
# Main Routing Function (UPDATED with session awareness)
# ============================================================================

async def route_to_agent(
    user_query: str, 
    session_id: str = None, 
    conversation_history: List[dict] = None
) -> Dict[str, Any]:
    """
    Main routing function with session awareness:
    1. Checks for active workflow in the session
    2. Fetches all active agents from database
    3. Detects subscription creation follow-ups
    4. Uses Ollama Llama 3.2 to select the correct agent
    5. Returns the selected agent code
    
    Returns:
        {
            "agent_code": "SUBSCRIPTIONCREATEAGENT" or None,
            "agent_name": "Subscription Creation Agent" or None,
            "confidence": 0.95,
            "reasoning": "...",
            "version": 68
        }
    """
    
    # Step 0: Clean up expired workflows periodically
    cleanup_expired_workflows()
    
    # Step 1: Check for active workflow in this session (HIGHEST PRIORITY)
    if session_id:
        active_agent = get_active_agent(session_id)
        if active_agent:
            logger.info(f"✅ Using active workflow agent: {active_agent} for session {session_id}")
            agents = await fetch_agents_from_database()
            agent = next((a for a in agents if a["team_code"] == active_agent), None)
            if agent:
                step = detect_workflow_step(user_query, conversation_history)
                continue_workflow(session_id, step)
                return {
                    "agent_code": active_agent,
                    "agent_name": agent["team_name"],
                    "confidence": 1.0,
                    "reasoning": f"Continuing active {active_agent} workflow (step: {step})",
                    "version": agent.get("version")
                }
    
    # Step 2: Get all agents from database
    agents = await fetch_agents_from_database()
    
    if not agents:
        logger.error("No agents found in database")
        return {
            "agent_code": None,
            "agent_name": None,
            "confidence": 0.0,
            "reasoning": "No agents registered in database. Please register agent teams via /api/agent-registry/register"
        }
    
    logger.info(f"Routing query '{user_query[:50]}...' with {len(agents)} available agents")
    
    # Step 3: Check if this is a subscription creation follow-up (SECOND PRIORITY)
    if is_subscription_followup(user_query, conversation_history):
        logger.info(f"🎯 Detected subscription creation follow-up: '{user_query}'")
        selected_code = "SUBSCRIPTIONCREATEAGENT"
        agent = next((a for a in agents if a["team_code"].upper() == selected_code), None)
        if agent:
            step = detect_workflow_step(user_query, conversation_history)
            # Start workflow if not already started (for follow-ups without active workflow)
            if session_id and not get_active_agent(session_id):
                start_workflow(session_id, selected_code, step)
            elif session_id:
                continue_workflow(session_id, step)
            return {
                "agent_code": selected_code,
                "agent_name": agent["team_name"],
                "confidence": 0.95,
                "reasoning": f"Subscription creation follow-up detected: '{user_query}' (step: {step})",
                "version": agent.get("version")
            }
    
    # Step 4: Fast-path for new subscription creation (THIRD PRIORITY)
    user_query_lower = user_query.lower()
    if is_subscription_creation_request(user_query):
        selected_code = "SUBSCRIPTIONCREATEAGENT"
        agent = next((a for a in agents if a["team_code"].upper() == selected_code), None)
        if agent:
            logger.info(f"🚀 Fast-path matched: SUBSCRIPTIONCREATEAGENT")
            if session_id:
                start_workflow(session_id, selected_code, step="awaiting_product")
            return {
                "agent_code": selected_code,
                "agent_name": agent["team_name"],
                "confidence": 1.0,
                "reasoning": "Routed via high-confidence keyword match for subscription creation",
                "version": agent.get("version")
            }
    
    # Step 5: Build prompt with database agents and call Ollama
    prompt = build_routing_prompt(user_query, agents)
    
    # Step 6: Call Ollama
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,
                    "max_tokens": 50
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama returned {response.status_code}: {response.text}")
                # Fall through to keyword fallback
                raise Exception(f"Ollama HTTP {response.status_code}")
            
            result = response.json()
            raw_response = result["response"]
            selected_code = raw_response.strip().upper()
            
            logger.info(f"Ollama selected: {selected_code}")
            
            # Validate the response against database agents
            valid_codes = [a["team_code"].upper() for a in agents]
            
            if selected_code in valid_codes:
                agent = next((a for a in agents if a["team_code"].upper() == selected_code), None)
                # Start workflow if this is a creation agent
                if selected_code == "SUBSCRIPTIONCREATEAGENT" and session_id:
                    start_workflow(session_id, selected_code, step="start")
                return {
                    "agent_code": selected_code,
                    "agent_name": agent["team_name"] if agent else selected_code,
                    "confidence": 0.95,
                    "reasoning": f"Successfully routed to {selected_code}",
                    "version": agent.get("version") if agent else None
                }
            elif selected_code == "UNKNOWN":
                # Fall through to keyword fallback
                raise Exception("Ollama returned UNKNOWN")
            else:
                logger.warning(f"Ollama returned invalid code: {selected_code}")
                raise Exception(f"Invalid code: {selected_code}")
                
    except (httpx.ConnectError, Exception) as e:
        logger.warning(f"Ollama unavailable or error: {e}. Using keyword-based fallback routing.")
        
        # Step 7: Keyword-based fallback routing (when Ollama is down)
        selected_agent = None
        user_query_lower = user_query.lower()
        
        # Check for payment/credit queries
        if any(kw in user_query_lower for kw in ["payment", "credit", "receivable", "invoice", "history", "limit", "outstanding", "overdue"]):
            selected_agent = next((a for a in agents if a["team_code"] == "ARCREDITAGENTTEAM"), None)
            if selected_agent:
                logger.info(f"Fallback matched: ARCREDITAGENTTEAM")
        
        # Check for subscription creation
        elif is_subscription_creation_request(user_query):
            selected_agent = next((a for a in agents if a["team_code"] == "SUBSCRIPTIONCREATEAGENT"), None)
            if selected_agent:
                logger.info(f"Fallback matched: SUBSCRIPTIONCREATEAGENT")
                if session_id:
                    start_workflow(session_id, "SUBSCRIPTIONCREATEAGENT", step="start")
        
        # Check for subscription follow-up (product names, dates, currencies, actions)
        elif is_subscription_followup(user_query, conversation_history):
            selected_agent = next((a for a in agents if a["team_code"] == "SUBSCRIPTIONCREATEAGENT"), None)
            if selected_agent:
                logger.info(f"Fallback matched: SUBSCRIPTIONCREATEAGENT (follow-up)")
                if session_id:
                    continue_workflow(session_id, detect_workflow_step(user_query, conversation_history))
        
        # Check for existing subscription queries
        elif any(kw in user_query_lower for kw in ["subscription", "renewal", "product", "lifecycle", "expiring", "billing", "view", "show me subscription"]):
            # Exclude creation keywords that might also be present
            if not is_subscription_creation_request(user_query):
                selected_agent = next((a for a in agents if a["team_code"] == "CX_OSS_SUBSCRIPTION_AUTHORING_TEAM_SPL"), None)
                if selected_agent:
                    logger.info(f"Fallback matched: CX_OSS_SUBSCRIPTION_AUTHORING_TEAM_SPL")
        
        # Check for collections queries
        elif any(kw in user_query_lower for kw in ["collection", "debt", "promise", "dispute", "arrangement"]):
            selected_agent = next((a for a in agents if a["team_code"] == "AGENTTEAMSCOLLECTORBUDDY"), None)
            if selected_agent:
                logger.info(f"Fallback matched: AGENTTEAMSCOLLECTORBUDDY")
        
        if selected_agent:
            return {
                "agent_code": selected_agent["team_code"],
                "agent_name": selected_agent["team_name"],
                "confidence": 0.7,
                "reasoning": f"Routed via keyword-based fallback (Ollama unavailable)",
                "version": selected_agent.get("version")
            }
        
        # No match found
        return {
            "agent_code": None,
            "agent_name": None,
            "confidence": 0.0,
            "reasoning": "Ollama service not available and no keywords matched. Please start Ollama with 'ollama serve'"
        }


# ============================================================================
# Utility Functions
# ============================================================================

def clear_agent_cache():
    """Clear the cached agents list to force fresh database fetch"""
    global _cache
    _cache = {"agents": None, "expiry": None}
    logger.info("Agent cache cleared")


def clear_all_workflows():
    """Clear all active workflows (useful for testing)"""
    global _active_workflows
    _active_workflows = {}
    logger.info("All workflows cleared")