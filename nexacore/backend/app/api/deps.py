"""
Shared FastAPI dependencies: DB session and current-user auth.
"""
import uuid
import hashlib
import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
logger = logging.getLogger(__name__)


def _auth_config_fingerprint() -> str:
    from app.core.config import settings

    return hashlib.sha256(settings.JWT_SECRET_KEY.encode()).hexdigest()[:12]


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    # Temporary production diagnostics: metadata only, never token/header data.
    def reject(stage: str, **details: object):
        logger.warning(
            "auth_rejected stage=%s path=%s config_fingerprint=%s details=%s",
            stage,
            request.url.path,
            _auth_config_fingerprint(),
            details,
        )
        raise credentials_exception

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        return reject("jwt_decode", payload_present=payload is not None)

    try:
        user_id = uuid.UUID(payload["sub"])
    except (TypeError, ValueError):
        return reject("subject_uuid", subject_type=type(payload.get("sub")).__name__)

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return reject("user_lookup", user_found=False)
    if not user.is_active or user.approval_status != "approved" or not user.email_verified:
        return reject(
            "user_status",
            user_found=True,
            is_active=user.is_active,
            approval_status=user.approval_status,
            email_verified=user.email_verified,
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
