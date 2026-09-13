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
from src.core.crypto import encrypt_secret
from src.database.models.auth import UserSession
from src.database.models.game import Game
from src.database.models.oidc_settings import OidcSettings
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/setup", tags=["setup"])
_SESSION_SECONDS = 30 * 24 * 60 * 60


class SetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)
    oidc_enabled: bool = False
    oidc_issuer_url: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_scopes: str = "openid profile email"
    oidc_redirect_uri: str | None = None
    oidc_groups_claim: str = "groups"
    oidc_admin_group: str | None = None
    oidc_user_match_field: str = "email"

    @field_validator("password")
    @classmethod
    def validate_setup_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("oidc_user_match_field")
    @classmethod
    def validate_oidc_user_match_field(cls, value: str) -> str:
        if value not in {"email", "username"}:
            raise ValueError("OIDC user matching must be email or username.")
        return value


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

    oidc_values = {
        "issuer_url": (payload.oidc_issuer_url or "").strip() or None,
        "client_id": (payload.oidc_client_id or "").strip() or None,
        "client_secret": (payload.oidc_client_secret or "").strip() or None,
        "scopes": payload.oidc_scopes.strip() or "openid profile email",
        "redirect_uri": (payload.oidc_redirect_uri or "").strip() or None,
        "groups_claim": payload.oidc_groups_claim.strip() or "groups",
        "admin_group": (payload.oidc_admin_group or "").strip() or None,
        "user_match_field": payload.oidc_user_match_field,
    }
    if payload.oidc_enabled and not all(
        (oidc_values["issuer_url"], oidc_values["client_id"], oidc_values["client_secret"])
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC requires an issuer URL, client ID, and client secret.",
        )
    if not payload.oidc_enabled and any(
        oidc_values[key] for key in ("issuer_url", "client_id", "client_secret")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enable OIDC before entering OIDC provider credentials.",
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
        await db.execute(update(Game).where(Game.user_id.is_(None)).values(user_id=user.id))

        if payload.oidc_enabled:
            client_secret = oidc_values["client_secret"]
            if not isinstance(client_secret, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OIDC requires a client secret.",
                )
            try:
                encrypted_client_secret = encrypt_secret(client_secret)
            except RuntimeError as exc:
                raise HTTPException(
                    status_code=400,
                    detail='SECRET_KEY must be a valid Fernet key before OIDC secrets can be saved. Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"',
                ) from exc
            oidc = OidcSettings(
                issuer_url=oidc_values["issuer_url"],
                client_id=oidc_values["client_id"],
                client_secret=encrypted_client_secret,
                scopes=oidc_values["scopes"],
                redirect_uri=oidc_values["redirect_uri"],
                groups_claim=oidc_values["groups_claim"],
                admin_group=oidc_values["admin_group"],
                user_match_field=oidc_values["user_match_field"],
            )
            db.add(oidc)

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
