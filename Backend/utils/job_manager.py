"""
In-memory Job Manager for async job tracking.
Stores job state during polling until completion or timeout.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Global job store: {job_id: {status, query, bearer_token, result, created_at, expires_at}}
_jobs: Dict[str, Dict[str, Any]] = {}

# Job expiration time (in seconds)
JOB_EXPIRATION_SECONDS = 3600  # 1 hour

# Max job age before cleanup (in seconds)
MAX_JOB_AGE_SECONDS = 7200  # 2 hours


def create_job(query: str, bearer_token: Optional[str] = None) -> str:
    """
    Create a new job and return its job_id.
    
    Args:
        query: The user query
        bearer_token: Optional bearer token for authentication
        
    Returns:
        job_id (uuid string)
    """
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    _jobs[job_id] = {
        "status": "QUEUED",
        "query": query,
        "bearer_token": bearer_token,
        "result": None,
        "error": None,
        "created_at": now,
        "expires_at": now + timedelta(seconds=JOB_EXPIRATION_SECONDS),
    }
    
    logger.info(f"Created job {job_id}: query='{query[:50]}...'")
    return job_id


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the current status of a job.
    
    Args:
        job_id: The job ID
        
    Returns:
        Job dict with status, or None if not found
    """
    if job_id not in _jobs:
        return None
    
    job = _jobs[job_id]
    
    # Check if job has expired
    if datetime.utcnow() > job["expires_at"]:
        logger.warning(f"Job {job_id} has expired")
        return None
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "created_at": job["created_at"].isoformat(),
        "expires_at": job["expires_at"].isoformat(),
    }


def update_job(job_id: str, status: str, result: Optional[Dict] = None, error: Optional[str] = None) -> bool:
    """
    Update job status and optionally result or error.
    
    Args:
        job_id: The job ID
        status: New status (QUEUED, RUNNING, COMPLETE, ERROR)
        result: Optional result dict when status is COMPLETE
        error: Optional error message when status is ERROR
        
    Returns:
        True if updated, False if job not found
    """
    if job_id not in _jobs:
        return False
    
    job = _jobs[job_id]
    job["status"] = status
    
    if result:
        job["result"] = result
    
    if error:
        job["error"] = error
    
    logger.info(f"Updated job {job_id}: status={status}")
    return True


def get_result(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the result of a completed job.
    
    Args:
        job_id: The job ID
        
    Returns:
        Result dict if job is COMPLETE, or None
    """
    if job_id not in _jobs:
        return None
    
    job = _jobs[job_id]
    
    if job["status"] == "COMPLETE":
        return job.get("result")
    
    return None


def get_error(job_id: str) -> Optional[str]:
    """
    Get the error of a failed job.
    
    Args:
        job_id: The job ID
        
    Returns:
        Error message if job has ERROR status, or None
    """
    if job_id not in _jobs:
        return None
    
    job = _jobs[job_id]
    
    if job["status"] == "ERROR":
        return job.get("error")
    
    return None


def get_bearer_token(job_id: str) -> Optional[str]:
    """
    Get the bearer token for a job.
    
    Args:
        job_id: The job ID
        
    Returns:
        Bearer token or None
    """
    if job_id not in _jobs:
        return None
    
    return _jobs[job_id].get("bearer_token")


def cleanup_expired_jobs() -> int:
    """
    Remove jobs that have been stored for too long.
    
    Returns:
        Number of jobs cleaned up
    """
    now = datetime.utcnow()
    expired_ids = [
        jid for jid, job in _jobs.items()
        if (now - job["created_at"]).total_seconds() > MAX_JOB_AGE_SECONDS
    ]
    
    for jid in expired_ids:
        del _jobs[jid]
    
    if expired_ids:
        logger.info(f"Cleaned up {len(expired_ids)} expired jobs")
    
    return len(expired_ids)
