import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.db.session import get_db
from app.models.discovery_event import DiscoveryEvent
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserOut, RegistrationResponse, EmailVerificationRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    is_first_user = db.query(User).count() == 0
    verification_token = None if is_first_user else secrets.token_urlsafe(32)
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="owner" if is_first_user else "user",
        is_active=is_first_user,
        approval_status="approved" if is_first_user else "pending",
        email_verified=is_first_user,
        verification_token=verification_token,
        verification_token_expiry=datetime.now(timezone.utc) + timedelta(hours=24) if verification_token else None,
    )
    db.add(user)
    db.flush()
    db.add(DiscoveryEvent(user_id=user.id, event_type="user_registered", payload=f'{{"approval_status":"{user.approval_status}"}}'))
    db.commit()
    db.refresh(user)
    return RegistrationResponse(
        user=user,
        verification_token=verification_token,
        message="Account created and approved as workspace owner." if is_first_user else "Account created. Verify your email, then wait for owner/admin approval.",
    )


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if user.approval_status != "approved" or not user.email_verified or not user.is_active:
        raise HTTPException(status_code=403, detail="Account verification and owner/admin approval are required")

    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role})
    logger.info(
        "auth_login_success user_id=%s role=%s config_fingerprint=%s",
        user.id,
        user.role,
        hashlib.sha256(settings.JWT_SECRET_KEY.encode()).hexdigest()[:12],
    )
    return Token(access_token=token)


@router.post("/verify-email")
def verify_email(payload: EmailVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == payload.token).first()
    now = datetime.now(timezone.utc)
    expiry = user.verification_token_expiry if user else None
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if user is None or expiry is None or expiry <= now:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expiry = None
    db.add(DiscoveryEvent(user_id=user.id, event_type="user_email_verified"))
    db.commit()
    return {"message": "Email verified. Owner/admin approval is still required.", "approval_status": user.approval_status}


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()

    return ForgotPasswordResponse(
        message="Password reset token generated for development use.",
        reset_token=reset_token,
    )


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == payload.reset_token).first()
    now = datetime.now(timezone.utc)
    if user is None or user.reset_token_expiry is None or user.reset_token_expiry <= now:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.commit()

    return {"message": "Password reset successfully"}
