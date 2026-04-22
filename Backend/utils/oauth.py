"""
OAuth2 Token Manager for Oracle Fusion Cloud.
Handles client credentials flow with automatic token caching and refresh.
"""

import time
import base64
import logging
import httpx
from Backend.config import get_settings

logger = logging.getLogger(__name__)

# ─── Token cache ────────────────────────────────────────────────────────────────
_token_cache: dict = {
    "access_token": None,
    "expires_at": 0,
}


async def get_oracle_token() -> str | None:
    """
    Obtain a valid OAuth2 bearer token for Oracle Fusion.
    Uses client credentials grant and caches the token until near expiry.
    Returns None if OAuth credentials are not fully configured.
    """
    settings = get_settings()

    # Check if OAuth is configured
    if not all([settings.OAUTH_TOKEN_URL, settings.OAUTH_CLIENT_ID, settings.OAUTH_CLIENT_SECRET]):
        return None

    # Return cached token if still valid (with 60s buffer)
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    logger.info("Requesting new OAuth2 token from Oracle IAM...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.OAUTH_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "scope": settings.OAUTH_SCOPE,
            },
            auth=(settings.OAUTH_CLIENT_ID, settings.OAUTH_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            logger.error(f"OAuth token request failed: {response.status_code} — {response.text}")
            raise Exception(f"Failed to obtain Oracle OAuth token: {response.status_code}")

        data = response.json()
        _token_cache["access_token"] = data["access_token"]
        _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)

        logger.info("OAuth2 token obtained successfully")
        return _token_cache["access_token"]


def get_basic_auth_header() -> str | None:
    """
    Generate a Basic Auth header using Fusion User ID and Password.
    Returns None if user/pass not configured.
    """
    settings = get_settings()
    if not settings.FUSION_USER or not settings.FUSION_PASSWORD:
        return None
    
    auth_str = f"{settings.FUSION_USER}:{settings.FUSION_PASSWORD}"
    encoded = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
    return f"Basic {encoded}"
