from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db import get_db
from models.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
)
from models.user import User, UserRead
from services.auth_service import (
    authenticate_user,
    create_audit_log,
    create_refresh_token,
    create_user,
    get_refresh_token,
    get_user_by_email,
    get_user_by_username,
    revoke_refresh_token,
)
from utils.security import create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(form_data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.username)
    refresh_token = create_refresh_token(db, user.id)
    create_audit_log(db, user.id, "login", "/api/auth/login")
    return Token(access_token=access_token, refresh_token=refresh_token.token, token_type="bearer")


@router.post("/refresh", response_model=Token)
async def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    refresh = get_refresh_token(db, payload.refresh_token)
    if not refresh or refresh.expires_at < datetime.utcnow():
        if refresh:
            revoke_refresh_token(db, payload.refresh_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == refresh.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.username)
    create_audit_log(db, user.id, "refresh_token", "/api/auth/refresh")
    return Token(access_token=access_token, refresh_token=refresh.token, token_type="bearer")


@router.post("/logout")
async def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    revoke_refresh_token(db, payload.refresh_token)
    return {"detail": "Logged out successfully"}


@router.post("/register", response_model=UserRead)
async def register(form_data: RegisterRequest, db: Session = Depends(get_db)):
    if get_user_by_username(db, form_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that username already exists.",
        )
    if get_user_by_email(db, form_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email already exists.",
        )

    user = create_user(db, form_data.username, form_data.email, form_data.password)
    create_audit_log(db, user.id, "register", "/api/auth/register")
    return user


@router.get("/me", response_model=UserRead)
async def me(current_user=Depends(get_current_user)):
    return current_user
