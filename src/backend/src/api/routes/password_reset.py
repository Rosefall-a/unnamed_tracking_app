from __future__ import annotations

import secrets
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import SESSION_COOKIE, hash_password, hash_token, validate_password
from src.core.config import settings
from src.core.email import send_email
from src.database.models.app_integration_settings import AppIntegrationSettings
from src.database.models.auth import UserSession
from src.database.models.password_reset import PasswordResetToken
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/auth/password-reset", tags=["auth"])
_RESET_SECONDS = 60 * 60
_SESSION_SECONDS = 30 * 24 * 60 * 60


class PasswordResetRequest(BaseModel):
    identifier: str = Field(min_length=1)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password(value)


def _public_app_origin(request: Request) -> str:
    """Prefer the browser-facing origin so Docker's internal backend hostname
    never leaks into password-reset emails."""
    origin = request.headers.get("origin", "").strip().rstrip("/")
    if origin:
        return origin
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",")[0].strip()
    if forwarded_host:
        return f"{forwarded_proto or 'http'}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


@router.get("/status")
async def password_reset_status(db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    settings_row = await db.scalar(select(AppIntegrationSettings).limit(1))
    enabled = bool(
        settings_row
        and settings_row.smtp_enabled
        and settings_row.password_reset_enabled
        and settings_row.smtp_host
        and settings_row.smtp_from_email
    )
    return {"enabled": enabled}


@router.post("/request")
async def request_password_reset(
    payload: PasswordResetRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    generic = "If an account matches that information, a password reset email has been sent."
    settings_row = await db.scalar(select(AppIntegrationSettings).limit(1))
    if (
        settings_row is None
        or not settings_row.smtp_enabled
        or not settings_row.password_reset_enabled
    ):
        return {"message": generic}
    identifier = payload.identifier.strip()
    user = await db.scalar(
        select(User).where((User.email == identifier.lower()) | (User.username == identifier))
    )
    if user is None or not user.is_active or not user.email:
        return {"message": generic}
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    raw_token = secrets.token_urlsafe(48)
    db.add(
        PasswordResetToken(
            id=uuid4(),
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=int(time.time()) + _RESET_SECONDS,
        )
    )
    await db.commit()
    reset_url = f"{_public_app_origin(request)}/reset-password?token={raw_token}"
    body = f"A password reset was requested for your Archive account.\n\nReset your password here:\n{reset_url}\n\nThis link expires in 1 hour. If you did not request this, you can safely ignore this email."
    try:
        send_email(settings_row, user.email, "Reset your Archive password", body)
    except Exception:
        return {"message": generic}
    return {"message": generic}


@router.post("/confirm")
async def confirm_password_reset(
    payload: PasswordResetConfirm, response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    token_hash = hash_token(payload.token)
    now = int(time.time())
    reset = await db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    )
    if reset is None:
        raise HTTPException(
            status_code=400, detail="This password reset link is invalid or has expired."
        )
    user = await db.scalar(select(User).where(User.id == reset.user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=400, detail="This password reset link is invalid or has expired."
        )
    user.password_hash = hash_password(payload.password)
    reset.used_at = now
    await db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    session_token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            user_id=user.id, token_hash=hash_token(session_token), expires_at=now + _SESSION_SECONDS
        )
    )
    await db.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=_SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
    )
    return {
        "message": "Your password has been reset. You are now signed in.",
        "user_id": str(user.id),
    }
