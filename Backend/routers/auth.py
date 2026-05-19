"""
Authentication Router — login and register endpoints.
"""

import hashlib
import secrets
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from db import SessionLocal, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, hash_hex = stored_hash.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return secrets.compare_digest(digest.hex(), hash_hex)


def create_access_token() -> str:
    return secrets.token_urlsafe(32)


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class AuthResponse(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    access_token: str


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.username == request.username) | (User.email == request.username)
        ).first()
        if user is None or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        access_token = create_access_token()
        logger.info(f"User logged in: {user.username}")
        return AuthResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            access_token=access_token,
        )
    finally:
        db.close()


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest) -> AuthResponse:
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(
            (User.username == request.username) | (User.email == request.email)
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="A user with that username or email already exists")

        user = User(
            username=request.username,
            email=request.email,
            password_hash=hash_password(request.password),
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        access_token = create_access_token()
        logger.info(f"Registered new user: {user.username}")
        return AuthResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            access_token=access_token,
        )
    finally:
        db.close()
