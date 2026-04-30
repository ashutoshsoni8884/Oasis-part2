"""
Oracle Agent Hub — FastAPI Backend
Entry point for the multi-agent router platform.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers.chat import router as chat_router

# ── Logging ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App ─────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Oracle Agent Hub API",
    description="Multi-agent router backend for Oracle Fusion Cloud AI Agent Studio",
    version="1.0.0",
)

# ── CORS ────────────────────────────────────────────────────────────────────────
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────────
app.include_router(chat_router)


# ── Health Check ────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        # "mock_mode": settings.MOCK_MODE,  # Only using real mode now
        "gemini_configured": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here"),
        "fusion_configured": bool(settings.FUSION_HOST and settings.FUSION_HOST != "your-fusion-host.fa.ocs.oraclecloud.com"),
    }


# ── Startup ─────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info("=" * 60)
    logger.info("  Oracle Agent Hub — Backend Starting")
    # logger.info(f"  Mode: {'🧪 MOCK' if settings.MOCK_MODE else '🔴 LIVE (Oracle Fusion)'}")
    logger.info("  Mode: 🔴 LIVE (Oracle Fusion - Real async flow)")
    logger.info(f"  Gemini: {'✅ Configured' if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != 'your-gemini-api-key-here' else '⚠️  Not configured (regex fallback)'}")
    logger.info(f"  Fusion Host: {settings.FUSION_HOST}")
    logger.info(f"  Agent Team: {settings.AGENT_TEAM_CODE} v{settings.AGENT_TEAM_VERSION}")
    logger.info("=" * 60)
