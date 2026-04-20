"""
Application configuration — loads from .env file.
Copy .env.example → .env and fill in your credentials.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Mode ────────────────────────────────────────────────────────────
    MOCK_MODE: bool = True

    # ── Google Gemini ───────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""

    # ── Oracle Fusion Cloud ─────────────────────────────────────────────
    FUSION_HOST: str = ""
    FUSION_USER: str = ""
    FUSION_PASSWORD: str = ""
    OAUTH_TOKEN_URL: str = ""
    OAUTH_CLIENT_ID: str = ""
    OAUTH_CLIENT_SECRET: str = ""
    OAUTH_SCOPE: str = ""

    # ── Oracle AI Agent Studio ──────────────────────────────────────────
    AGENT_TEAM_CODE: str = ""
    AGENT_TEAM_VERSION: int = 1

    # ── Server ──────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
