"""
Session State Manager - Tracks active agent workflows per conversation
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# Store active workflows: {session_id: {"agent_code": str, "step": str, "expires_at": datetime}}
_active_workflows: Dict[str, Dict] = {}
WORKFLOW_TIMEOUT_SECONDS = 1800  # 30 minutes - enough for subscription creation

class SessionManager:
    @staticmethod
    def start_workflow(session_id: str, agent_code: str, step: str = "start"):
        """Start or continue a workflow for a session"""
        _active_workflows[session_id] = {
            "agent_code": agent_code,
            "step": step,
            "started_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(seconds=WORKFLOW_TIMEOUT_SECONDS),
            "message_count": 1
        }
        logger.info(f"Started workflow: session={session_id}, agent={agent_code}, step={step}")
    
    @staticmethod
    def continue_workflow(session_id: str, step: str = None):
        """Update an existing workflow"""
        if session_id in _active_workflows:
            workflow = _active_workflows[session_id]
            if step:
                workflow["step"] = step
            workflow["message_count"] += 1
            workflow["expires_at"] = datetime.utcnow() + timedelta(seconds=WORKFLOW_TIMEOUT_SECONDS)
            logger.info(f"Continued workflow: session={session_id}, agent={workflow['agent_code']}, step={workflow['step']}")
            return workflow["agent_code"]
        return None
    
    @staticmethod
    def get_active_agent(session_id: str) -> Optional[str]:
        """Get the currently active agent for a session"""
        if session_id in _active_workflows:
            workflow = _active_workflows[session_id]
            if datetime.utcnow() < workflow["expires_at"]:
                return workflow["agent_code"]
            else:
                # Workflow expired
                del _active_workflows[session_id]
                logger.info(f"Workflow expired: session={session_id}")
        return None
    
    @staticmethod
    def end_workflow(session_id: str):
        """End a workflow (e.g., after completion or cancellation)"""
        if session_id in _active_workflows:
            agent = _active_workflows[session_id]["agent_code"]
            del _active_workflows[session_id]
            logger.info(f"Ended workflow: session={session_id}, agent={agent}")
    
    @staticmethod
    def cleanup_expired():
        """Clean up expired workflows"""
        now = datetime.utcnow()
        expired = [sid for sid, w in _active_workflows.items() if now > w["expires_at"]]
        for sid in expired:
            del _active_workflows[sid]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired workflows")