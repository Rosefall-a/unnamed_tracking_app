from __future__ import annotations

import secrets
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import hash_password, hash_token, validate_password
from src.core.email import send_email
from src.database.models.app_integration_settings import AppIntegrationSettings
from src.database.models.auth import UserSession
from src.database.models.password_reset import PasswordResetToken
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/auth/password-reset", tags=["auth"])
_RESET_SECONDS = 60 * 60


class PasswordResetRequest(BaseModel):
    identifier: str = Field(min_length=1)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password(value)


@router.post("/request")
async def request_password_reset(payload: PasswordResetRequest, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    generic = "If an account matches that information, a password reset email has been sent."
    settings = await db.scalar(select(AppIntegrationSettings).limit(1))
    if settings is None or not settings.smtp_enabled:
        return {"message": generic}
    identifier = payload.identifier.strip()
    user = await db.scalar(select(User).where((User.email == identifier.lower()) | (User.username == identifier)))
    if user is None or not user.is_active or not user.email:
        return {"message": generic}
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    raw_token = secrets.token_urlsafe(48)
    db.add(PasswordResetToken(id=uuid4(), user_id=user.id, token_hash=hash_token(raw_token), expires_at=int(time.time()) + _RESET_SECONDS))
    await db.commit()
    base_url = str(request.base_url).rstrip("/")
    reset_url = f"{base_url}/reset-password?token={raw_token}"
    body = f"A password reset was requested for your Archive account.\n\nReset your password here:\n{reset_url}\n\nThis link expires in 1 hour. If you did not request this, you can safely ignore this email."
    try:
        send_email(settings, user.email, "Reset your Archive password", body)
    except Exception:
        return {"message": generic}
    return {"message": generic}


@router.post("/confirm")
async def confirm_password_reset(payload: PasswordResetConfirm, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    token_hash = hash_token(payload.token)
    now = int(time.time())
    reset = await db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash, PasswordResetToken.used_at.is_(None), PasswordResetToken.expires_at > now))
    if reset is None:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")
    user = await db.scalar(select(User).where(User.id == reset.user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")
    user.password_hash = hash_password(payload.password)
    reset.used_at = now
    await db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    await db.commit()
    return {"message": "Your password has been reset. You can now sign in."}
