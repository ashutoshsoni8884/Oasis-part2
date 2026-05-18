"""
Oracle Agent Hub — FastAPI Backend
Entry point for the multi-agent router platform.
"""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException as FastAPIHTTPException

# Add the Backend directory to sys.path so local imports work
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config import get_settings
from logger import logger
from middleware.logging_middleware import LoggingMiddleware
from middleware.exception_handlers import (
    global_exception_handler,
    http_exception_handler,
    starlette_http_exception_handler
)
from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.agents import router as agents_router
from routers.agent_registry import router as agent_registry_router

# ── App ─────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Oracle Agent Hub API",
    description="Multi-agent router backend for Oracle Fusion Cloud AI Agent Studio",
    version="1.0.0",
)

# ── Middleware ─────────────────────────────────────────────────────────────────
# Add logging middleware (must be first)
app.add_middleware(LoggingMiddleware)

# Add CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ──────────────────────────────────────────────────────────
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(FastAPIHTTPException, http_exception_handler)
from starlette.exceptions import HTTPException as StarletteHTTPException
app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)

# ── Routers ─────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(agents_router)
app.include_router(agent_registry_router)


# ── Health Check ────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        # "mock_mode": settings.MOCK_MODE,  # Only using real mode now
        "fusion_configured": bool(settings.FUSION_HOST and settings.FUSION_HOST != "your-fusion-host.fa.ocs.oraclecloud.com"),
    }


# ── Startup ─────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info("=" * 60)
    logger.info("  Oracle Agent Hub — Backend Starting")
    # logger.info(f"  Mode: {'🧪 MOCK' if settings.MOCK_MODE else '🔴 LIVE (Oracle Fusion)'}")
    logger.info("  Mode: 🔴 LIVE (Oracle Fusion - Real async flow)")
    logger.info(f"  Fusion Host: {settings.FUSION_HOST}")
    logger.info(f"  Agent Team: {settings.AGENT_TEAM_CODE} v{settings.AGENT_TEAM_VERSION}")
    logger.info(f"  DB Logging: {'✅ Enabled' if settings.ENABLE_DB_LOGGING else '❌ Disabled'}")
    logger.info(f"  File Logging: {'✅ Enabled' if settings.ENABLE_FILE_LOGGING else '❌ Disabled'}")
    logger.info("=" * 60)
