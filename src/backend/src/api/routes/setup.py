from __future__ import annotations

import secrets
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.application_backup import (
    application_backup_path,
    preview_application_backup,
    restore_application_backup,
)
from src.api.routes.settings import get_or_create_app_integration_settings
from src.core.auth import (
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    hash_password,
    hash_token,
    validate_password,
)
from src.core.config import settings
from src.core.crypto import encrypt_secret
from src.core.setup_config import default_setup_configuration
from src.database.models.auth import UserSession
from src.database.models.game import Game
from src.database.models.oidc_settings import OidcSettings
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/setup", tags=["setup"])
setup_configuration = default_setup_configuration()


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
    oidc_allow_new_users: bool = True
    oidc_button_text: str = "Continue with SSO"
    oidc_button_image_url: str | None = None
    oidc_button_color: str = "#d68a34"
    oidc_provider_enabled: bool = True
    oidc_show_on_login: bool = True
    oidc_autostart_enabled: bool = True
    oidc_default_login_method: str = "local"
    smtp_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_from_email: str | None = None
    smtp_from_name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_setup_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("smtp_port")
    @classmethod
    def validate_smtp_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("SMTP port must be between 1 and 65535.")
        return value

    @field_validator("oidc_user_match_field")
    @classmethod
    def validate_oidc_user_match_field(cls, value: str) -> str:
        if value not in {"email", "username"}:
            raise ValueError("OIDC user matching must be email or username.")
        return value


@router.get("/status")
async def setup_status(db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    has_user = await db.scalar(select(User.id).limit(1)) is not None
    ui_enabled = setup_configuration.setup_enabled(settings.SETUP_MODE)
    return {"setup_required": not has_user and ui_enabled, "setup_ui_enabled": ui_enabled}


@router.get("/application-backup")
async def application_backup_status() -> dict[str, bool]:
    return {"available": application_backup_path().is_file()}


@router.get("/application-backup/file")
async def application_backup_file() -> Response:
    path = application_backup_path()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No preconfigured application backup was found.")
    return Response(content=path.read_bytes(), media_type="application/json")


@router.post("/application-backup/preview")
async def application_backup_preview(
    password: str = Form(..., min_length=12, max_length=256),
    application_file: UploadFile | None = File(None),
) -> dict:
    raw = await application_file.read() if application_file else (
        application_backup_path().read_bytes() if application_backup_path().is_file() else b""
    )
    if not raw:
        raise HTTPException(status_code=404, detail="No application backup was provided.")
    try:
        return preview_application_backup(raw, password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import-application")
async def import_application_backup(
    password: str = Form(..., min_length=12, max_length=256),
    application_file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    raw = await application_file.read() if application_file else (
        application_backup_path().read_bytes() if application_backup_path().is_file() else b""
    )
    if not raw:
        raise HTTPException(status_code=404, detail="No application backup was provided.")
    try:
        return await restore_application_backup(db, raw, password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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

    smtp_host = (payload.smtp_host or "").strip() or None
    smtp_from_email = (payload.smtp_from_email or "").strip() or None
    smtp_username = (payload.smtp_username or "").strip() or None
    smtp_password = (payload.smtp_password or "").strip() or None
    smtp_from_name = (payload.smtp_from_name or "").strip() or None
    if payload.smtp_enabled and (not smtp_host or not smtp_from_email):
        raise HTTPException(status_code=400, detail="SMTP requires a host and sender email address.")

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
                allow_new_users=payload.oidc_allow_new_users,
                login_button_text=payload.oidc_button_text.strip() or "Continue with SSO",
                default_login_method=payload.oidc_default_login_method,
            )
            db.add(oidc)

        if payload.smtp_enabled:
            app_integrations = await get_or_create_app_integration_settings(db)
            app_integrations.smtp_enabled = True
            app_integrations.smtp_host = smtp_host
            app_integrations.smtp_port = payload.smtp_port
            app_integrations.smtp_username = smtp_username
            app_integrations.smtp_password = encrypt_secret(smtp_password) if smtp_password else None
            app_integrations.smtp_use_tls = payload.smtp_use_tls
            app_integrations.smtp_use_ssl = payload.smtp_use_ssl
            app_integrations.smtp_from_email = smtp_from_email
            app_integrations.smtp_from_name = smtp_from_name

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
