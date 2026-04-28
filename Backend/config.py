"""
Application configuration — loads from .env file.
Copy .env.example → .env and fill in your credentials.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # ── Mode ────────────────────────────────────────────────────────────
    # MOCK_MODE: bool = True  # Commented out - using real Oracle Fusion only
    
    # Keeping MOCK_MODE for backwards compatibility but defaulting to False
    MOCK_MODE: bool = False

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

    # ── JSON Web Token (JWT) Auth ─────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-to-a-secure-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080
    PASSWORD_SALT: str = "oasis-default-salt"

    # ── Oracle AI Agent Studio ──────────────────────────────────────────
    AGENT_TEAM_CODE: str = ""
    AGENT_TEAM_VERSION: int = 1

    # ── Database ───────────────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "oasisdb"
    DB_USER: str = "oasis_user"
    DB_PASSWORD: str = "8884"

    # ── Server ──────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ]

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
