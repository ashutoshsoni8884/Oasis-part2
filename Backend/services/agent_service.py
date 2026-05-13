"""
Agent Service — resolves which Oracle agent teams are known and allowed
for a given user, based on environment configuration.

This is intentionally simple and env-driven for now:
- AVAILABLE_AGENT_TEAM_CODES: comma-separated list of Oracle team codes
- DEFAULT_ALLOWED_AGENT_TEAM_CODES: optional comma-separated default allowlist

Future-ready: this module can later be extended to query DB tables
for users, roles, agents, and user_agents without changing callers.
"""

from __future__ import annotations

from typing import Iterable, List, Set

from fastapi import HTTPException, status

from Backend.config import get_settings
from Backend.models.user import User


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def get_known_agents() -> List[str]:
    """
    Return all agent_team_codes this backend knows about.

    Source of truth is env config:
    - AVAILABLE_AGENT_TEAM_CODES: comma-separated list
    - If empty, fall back to AGENT_TEAM_CODE for single-agent mode.
    """
    settings = get_settings()
    codes = _split_csv(settings.AVAILABLE_AGENT_TEAM_CODES)
    if codes:
        return codes

    # Single-agent fallback for backward compatibility
    if settings.AGENT_TEAM_CODE:
        return [settings.AGENT_TEAM_CODE]

    return []


def get_allowed_agents(user: User | None) -> List[str]:
    """
    Return the list of agent_team_codes the given user is allowed to access.

    Current placeholder rules (env-driven):
    - If DEFAULT_ALLOWED_AGENT_TEAM_CODES is set: use that intersection
      with known agents.
    - Else: all known agents are allowed.
    - If no known agents, returns an empty list.
    """
    settings = get_settings()
    known: Set[str] = set(get_known_agents())
    if not known:
        return []

    default_allowed = _split_csv(settings.DEFAULT_ALLOWED_AGENT_TEAM_CODES)
    if default_allowed:
        allowed = known.intersection(default_allowed)
        return sorted(allowed)

    # By default, allow all known agents; user- and role-specific logic
    # can be layered here in a future DB-backed implementation.
    return sorted(known)


def validate_agent_access(user: User | None, agent_team_code: str | None) -> str:
    """
    Validate that:
    - a non-empty agent_team_code is provided, and
    - it is within the caller's allowed agents.

    Returns the effective agent_team_code on success,
    or raises HTTP 400/403 on failure.
    """
    if not agent_team_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="agent_team_code is required when no default agent is configured.",
        )

    allowed = set(get_allowed_agents(user))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No agents are configured for this environment.",
        )

    if agent_team_code not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized agent access",
        )

    return agent_team_code


def get_agent_config(agent_team_code: str) -> dict:
    """
    Return minimal config for the given agent_team_code.

    For now this is just a simple dict; in a future iteration this
    can pull richer metadata from a DB-backed `agents` table.
    """
    return {
        "agent_team_code": agent_team_code,
    }

