import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    approval_status: str
    email_verified: bool
    approved_at: datetime | None = None
    rejection_reason: str | None = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegistrationResponse(BaseModel):
    user: UserOut
    verification_token: str | None = None
    message: str


class EmailVerificationRequest(BaseModel):
    token: str


class UserApprovalRequest(BaseModel):
    role: str = "agent"
    reason: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8)
