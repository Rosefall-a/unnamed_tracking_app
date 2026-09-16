from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.settings import get_or_create_app_integration_settings
from src.core.auth import get_current_admin
from src.core.crypto import encrypt_secret
from src.core.email import send_email
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/settings/smtp", tags=["settings"])
logger = logging.getLogger(__name__)


class SmtpSettingsRequest(BaseModel):
    enabled: bool
    host: str | None = None
    port: int = Field(default=587, ge=1, le=65535)
    username: str | None = None
    password: str | None = None
    use_tls: bool = True
    use_ssl: bool = False
    from_email: str | None = None
    from_name: str | None = None
    password_reset_enabled: bool = True


def _view(row) -> dict[str, object]:
    return {
        "enabled": row.smtp_enabled,
        "host": row.smtp_host,
        "port": row.smtp_port,
        "username": row.smtp_username,
        "password_configured": bool(row.smtp_password),
        "use_tls": row.smtp_use_tls,
        "use_ssl": row.smtp_use_ssl,
        "from_email": row.smtp_from_email,
        "from_name": row.smtp_from_name,
        "password_reset_enabled": row.password_reset_enabled,
    }


@router.get("")
async def get_smtp_settings(
    db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)
) -> dict[str, object]:
    return _view(await get_or_create_app_integration_settings(db))


@router.put("")
async def update_smtp_settings(
    payload: SmtpSettingsRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict[str, object]:
    row = await get_or_create_app_integration_settings(db)
    row.smtp_enabled = payload.enabled
    row.smtp_host = (payload.host or "").strip() or None
    row.smtp_port = payload.port
    row.smtp_username = (payload.username or "").strip() or None
    if payload.password:
        row.smtp_password = encrypt_secret(payload.password)
    row.smtp_use_tls = payload.use_tls
    row.smtp_use_ssl = payload.use_ssl
    row.smtp_from_email = (payload.from_email or "").strip() or None
    row.smtp_from_name = (payload.from_name or "").strip() or None
    row.password_reset_enabled = payload.password_reset_enabled
    await db.commit()
    return _view(row)


@router.post("/test")
async def test_smtp(
    db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)
) -> dict[str, str]:
    row = await get_or_create_app_integration_settings(db)
    if not row.smtp_enabled or not row.smtp_host or not row.smtp_from_email:
        raise HTTPException(400, "SMTP must be enabled with a host and sender email first.")
    if not admin.email:
        raise HTTPException(400, "Your admin account needs an email address for the test message.")
    try:
        await asyncio.to_thread(
            send_email,
            row,
            admin.email,
            "Archive SMTP test",
            "Your Archive SMTP settings are working.",
        )
    except Exception as exc:
        logger.exception("SMTP test email could not be sent")
        raise HTTPException(502, "SMTP test failed. Check the server logs for details.") from exc
    return {"message": f"Test email sent to {admin.email}."}
