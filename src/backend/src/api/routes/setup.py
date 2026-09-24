from __future__ import annotations

import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import (
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    hash_password,
    hash_token,
    validate_password,
)
from src.core.config import settings
from src.core.crypto import encrypt_secret
from src.core.env_handler import EnvConfigHandler
from src.database.models.auth import UserSession
from src.database.models.game import Game
from src.database.models.oidc_settings import OidcSettings
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/setup", tags=["setup"])


class SetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)
    oidc_enabled: bool = False
    oidc_name: str | None = None
    oidc_issuer_url: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_scopes: str = "openid profile email"
    oidc_redirect_uri: str | None = None
    oidc_groups_claim: str = "groups"
    oidc_admin_group: str | None = None
    oidc_user_match_field: str = "email"
    oidc_allow_new_users: bool = True
    oidc_button_text: str = "Continue with SSO"
    oidc_button_image_url: str | None = None
    oidc_button_color: str = "#d68a34"
    oidc_provider_enabled: bool = True
    oidc_show_on_login: bool = True
    oidc_autostart_enabled: bool = True
    oidc_default_login_method: str = "local"

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

    @field_validator("oidc_default_login_method")
    @classmethod
    def validate_oidc_default_login_method(cls, value: str) -> str:
        if value not in {"local", "sso"}:
            raise ValueError("OIDC default login method must be local or sso.")
        return value


@router.get("/configuration")
async def setup_configuration() -> dict[str, object]:
    """Return setup metadata, resolved non-secret values, and environment locks."""
    from src.core.env_handler import EnvConfigHandler

    handler = EnvConfigHandler()
    settings_data = []
    for item in handler.setup_schema():
        name = str(item["name"])
        spec_value = handler.get(name)
        env_set = handler.has(name)
        item["locked"] = env_set
        if not bool(item["secret"]):
            item["resolved"] = spec_value
            if env_set:
                item["default"] = spec_value
        settings_data.append(item)
    return {
        "settings": settings_data,
        "startup_mode": handler.mode.value,
        "startup_ui": "forced" if handler.startup_ui_forced else "auto",
        "forced": handler.startup_ui_forced,
    }


@router.get("/status")
async def setup_status(db: AsyncSession = Depends(get_db)) -> dict[str, bool | str]:
    has_user = await db.scalar(select(User.id).limit(1)) is not None
    handler = EnvConfigHandler()
    return {
        "setup_required": not has_user,
        "startup_ui": "forced" if handler.startup_ui_forced else "auto",
        "forced": handler.startup_ui_forced,
    }


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
    handler = EnvConfigHandler()
    env_oidc = {
        "issuer_url": handler.has("OIDC_ISSUER_URL"),
        "client_id": handler.has("OIDC_CLIENT_ID"),
        "client_secret": handler.has("OIDC_CLIENT_SECRET"),
        "scopes": handler.has("OIDC_SCOPES"),
        "redirect_uri": handler.has("OIDC_REDIRECT_URI"),
        "groups_claim": handler.has("OIDC_GROUPS_CLAIM"),
        "admin_group": handler.has("OIDC_ADMIN_GROUP"),
        "user_match_field": handler.has("OIDC_USER_MATCH_FIELD"),
    }
    if handler.has("OIDC_ISSUER_URL"):
        payload.oidc_enabled = True
    if payload.oidc_enabled and not all(
        (
            oidc_values["issuer_url"] or handler.has("OIDC_ISSUER_URL"),
            oidc_values["client_id"] or handler.has("OIDC_CLIENT_ID"),
            oidc_values["client_secret"] or handler.has("OIDC_CLIENT_SECRET"),
        )
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
            client_secret = oidc_values["client_secret"] or handler.get("OIDC_CLIENT_SECRET")
            issuer_url = oidc_values["issuer_url"] or handler.get("OIDC_ISSUER_URL")
            client_id = oidc_values["client_id"] or handler.get("OIDC_CLIENT_ID")
            if not isinstance(client_secret, str) or not isinstance(issuer_url, str) or not isinstance(client_id, str):
                raise HTTPException(status_code=400, detail="OIDC requires an issuer URL, client ID, and client secret.")
            encrypted_client_secret = encrypt_secret(client_secret)
            provider_name = (payload.oidc_name if hasattr(payload, "oidc_name") else None) or issuer_url
            provider_slug = "".join(c if c.isalnum() else "-" for c in provider_name.lower()).strip("-")[:80] or "oidc"
            oidc = OidcSettings(
                issuer_url=issuer_url,
                client_id=client_id,
                client_secret=encrypted_client_secret,
                scopes=oidc_values["scopes"] or str(handler.get("OIDC_SCOPES") or "openid profile email"),
                redirect_uri=oidc_values["redirect_uri"] or handler.get("OIDC_REDIRECT_URI"),
                groups_claim=oidc_values["groups_claim"] or str(handler.get("OIDC_GROUPS_CLAIM") or "groups"),
                admin_group=oidc_values["admin_group"] or handler.get("OIDC_ADMIN_GROUP"),
                user_match_field=oidc_values["user_match_field"] or str(handler.get("OIDC_USER_MATCH_FIELD") or "email"),
                default_login_method=payload.oidc_default_login_method,
                login_button_text=payload.oidc_button_text.strip() or "Continue with SSO",
                allow_new_users=payload.oidc_allow_new_users,
                providers_json=json.dumps([{
                    "name": provider_name,
                    "slug": provider_slug,
                    "issuer_url": issuer_url,
                    "client_id": client_id,
                    "client_secret": encrypted_client_secret,
                    "scopes": oidc_values["scopes"] or str(handler.get("OIDC_SCOPES") or "openid profile email"),
                    "redirect_uri": oidc_values["redirect_uri"] or handler.get("OIDC_REDIRECT_URI"),
                    "groups_claim": oidc_values["groups_claim"] or str(handler.get("OIDC_GROUPS_CLAIM") or "groups"),
                    "admin_group": oidc_values["admin_group"] or handler.get("OIDC_ADMIN_GROUP"),
                    "user_match_field": oidc_values["user_match_field"] or str(handler.get("OIDC_USER_MATCH_FIELD") or "email"),
                    "allow_new_users": payload.oidc_allow_new_users,
                    "button_text": payload.oidc_button_text.strip() or "Continue with SSO",
                    "button_image_url": (payload.oidc_button_image_url or "").strip() or None,
                    "button_color": payload.oidc_button_color,
                    "enabled": payload.oidc_provider_enabled,
                    "show_on_login": payload.oidc_show_on_login,
                    "autostart_enabled": payload.oidc_autostart_enabled,
                }]),
            )
            db.add(oidc)

        session_token = secrets.token_urlsafe(32)
        db.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_token(session_token),
                expires_at=int(time.time()) + SESSION_TTL_SECONDS,
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
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
    )
    return {"status": "setup_complete", "user_id": str(user.id), "is_admin": True}
