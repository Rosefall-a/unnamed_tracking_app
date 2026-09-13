from __future__ import annotations

import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import SESSION_COOKIE, hash_password, hash_token, validate_password
from src.core.config import settings
from src.database.models.game import Game
from src.database.models.auth import UserSession
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/setup", tags=["setup"])
_SESSION_SECONDS = 30 * 24 * 60 * 60


class SetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_setup_password(cls, value: str) -> str:
        return validate_password(value)


@router.get("/status")
async def setup_status(db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    has_user = await db.scalar(select(User.id).limit(1)) is not None
    return {"setup_required": not has_user}


@router.post("", status_code=status.HTTP_201_CREATED)
async def setup_admin(
    payload: SetupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | bool]:
    # Serialize first-run setup so two simultaneous browser requests cannot
    # create competing administrator accounts.
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext('unnamed_tracking_app_setup'))"))

    if await db.scalar(select(User.id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Setup is already complete."
        )

    username = payload.username.strip()
    email = payload.email.strip().lower()
    if not username or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and email are required.",
        )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_admin=True,
    )
    db.add(user)
    try:
        await db.flush()
        # A fresh database may have rows imported before authentication was
        # configured. Attach those orphaned games to the first administrator.
        await db.execute(update(Game).where(Game.user_id.is_(None)).values(user_id=user.id))

        session_token = secrets.token_urlsafe(32)
        db.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_token(session_token),
                expires_at=int(time.time()) + _SESSION_SECONDS,
            )
        )
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists.",
        ) from exc

    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=_SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
    )
    return {"status": "setup_complete", "user_id": str(user.id), "is_admin": True}
