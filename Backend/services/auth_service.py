import logging
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from config import get_settings
from models.authorization import AuditLog, Permission, RefreshToken, Role, RolePermission, UserRole
from models.user import User
from utils.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def create_user(db: Session, username: str, email: str, password: str) -> User:
    hashed_password = get_password_hash(password)
    user = User(
        username=username,
        email=email,
        password_hash=hashed_password,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Created new user: {username}")
    return user


def get_refresh_token(db: Session, token: str) -> RefreshToken | None:
    return db.query(RefreshToken).filter(RefreshToken.token == token).first()


def create_refresh_token(db: Session, user_id: int) -> RefreshToken:
    settings = get_settings()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = RefreshToken(
        user_id=user_id,
        token=secrets.token_urlsafe(48),
        expires_at=expires_at,
    )
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    return refresh_token


def revoke_refresh_token(db: Session, token: str) -> None:
    refresh_token = get_refresh_token(db, token)
    if refresh_token:
        db.delete(refresh_token)
        db.commit()


def create_audit_log(db: Session, user_id: int | None, action: str, endpoint: str) -> AuditLog:
    audit_log = AuditLog(user_id=user_id, action=action, endpoint=endpoint)
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log


def get_role_by_name(db: Session, role_name: str) -> Role | None:
    return db.query(Role).filter(Role.role_name == role_name).first()


def create_role_if_missing(db: Session, role_name: str) -> Role:
    role = get_role_by_name(db, role_name)
    if role:
        return role
    role = Role(role_name=role_name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def assign_role_to_user(db: Session, user_id: int, role_name: str) -> UserRole:
    role = create_role_if_missing(db, role_name)
    existing = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role.id).first()
    if existing:
        return existing
    assignment = UserRole(user_id=user_id, role_id=role.id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def grant_permission_to_role(db: Session, role_id: int, permission_name: str) -> RolePermission:
    permission = db.query(Permission).filter(Permission.permission_name == permission_name).first()
    if not permission:
        permission = Permission(permission_name=permission_name)
        db.add(permission)
        db.commit()
        db.refresh(permission)

    existing = db.query(RolePermission).filter(
        RolePermission.role_id == role_id,
        RolePermission.permission_id == permission.id,
    ).first()
    if existing:
        return existing

    assignment = RolePermission(role_id=role_id, permission_id=permission.id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment

