"""Password-protected export of deployment configuration and secrets.

This backup deliberately contains deployment settings and encryption material,
not users, sessions, libraries, media, or other user-owned data. The returned
file is encrypted before it leaves the server.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.settings import get_or_create_app_integration_settings
from src.core.auth import get_current_admin
from src.core.config import settings as app_settings
from src.core.crypto import decrypt_secret
from src.database.models.oidc_settings import OidcSettings
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(
    prefix="/api/settings/backup",
    tags=["settings"],
    dependencies=[Depends(get_current_admin)],
)

_KDF_ITERATIONS = 600_000
_SALT_BYTES = 16
_MIN_PASSWORD_LENGTH = 12
_SECRET_APP_FIELDS = {
    "steamgriddb_api_key",
    "retroachievements_api_key",
    "giantbomb_api_key",
    "igdb_client_secret",
    "screenscraper_sspassword",
    "screenscraper_devpassword",
    "xbox_client_secret",
    "smtp_password",
}


class SecretBackupRequest(BaseModel):
    password: str = Field(min_length=_MIN_PASSWORD_LENGTH, max_length=256)


def _decrypt(value: str | None) -> str | None:
    if not value:
        return None
    return decrypt_secret(value)


def _serialize_model(row: Any, secret_fields: set[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if column.name in secret_fields:
            value = _decrypt(value)
        elif hasattr(value, "hex") and not isinstance(value, (str, bytes)):
            value = str(value)
        result[column.name] = value
    return result


def _oidc_export(row: OidcSettings) -> dict[str, Any]:
    result = _serialize_model(row, {"client_secret"})
    providers: list[dict[str, Any]] = []
    try:
        raw = json.loads(row.providers_json or "[]")
    except (TypeError, ValueError) as exc:
        raise HTTPException(500, "Saved OIDC provider configuration is invalid.") from exc
    if not isinstance(raw, list):
        raise HTTPException(500, "Saved OIDC provider configuration is invalid.")
    for provider in raw:
        if not isinstance(provider, dict):
            raise HTTPException(500, "Saved OIDC provider configuration is invalid.")
        item = dict(provider)
        if item.get("client_secret"):
            item["client_secret"] = _decrypt(str(item["client_secret"]))
        providers.append(item)
    result["providers_json"] = json.dumps(providers)
    return result


def _key_copies() -> list[str]:
    config_dir = Path(app_settings.APP_DATA_DIR if hasattr(app_settings, "APP_DATA_DIR") else "/data") / "config"
    values = []
    for name in ("fernet.key", "fernet.key.1", "fernet.key.2"):
        path = config_dir / name
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise HTTPException(500, "Persistent Fernet key copies could not be read.") from exc
        try:
            Fernet(value.encode())
        except (ValueError, TypeError) as exc:
            raise HTTPException(500, "A persistent Fernet key copy is invalid.") from exc
        values.append(value)
    return values


def _password_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


@router.post("/export")
async def export_secret_backup(
    payload: SecretBackupRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> Response:
    del admin
    app = await get_or_create_app_integration_settings(db)
    oidc = await db.scalar(select(OidcSettings).limit(1))
    if oidc is None:
        oidc = OidcSettings()

    backup = {
        "format": "archive-deployment-backup",
        "format_version": 1,
        "exported_at": int(time.time()),
        "scope": {
            "includes": [
                "deployment application settings",
                "provider credentials",
                "SMTP credentials",
                "OIDC configuration and provider secrets",
                "persistent Fernet encryption keys",
            ],
            "excludes": [
                "users",
                "sessions",
                "user credentials and API keys",
                "libraries and games",
                "media and uploaded files",
                "user preferences and scan settings",
                "database connection credentials",
            ],
        },
        "app_integration_settings": _serialize_model(app, _SECRET_APP_FIELDS),
        "oidc_settings": _oidc_export(oidc),
        "fernet_keys": _key_copies(),
    }

    plaintext = json.dumps(backup, sort_keys=True, separators=(",", ":")).encode("utf-8")
    salt = secrets.token_bytes(_SALT_BYTES)
    token = Fernet(_password_key(payload.password, salt)).encrypt(plaintext)
    envelope = {
        "format": "archive-deployment-backup-encrypted",
        "format_version": 1,
        "kdf": "PBKDF2-HMAC-SHA256",
        "iterations": _KDF_ITERATIONS,
        "salt": base64.urlsafe_b64encode(salt).decode("ascii"),
        "ciphertext": token.decode("ascii"),
    }
    body = (json.dumps(envelope, sort_keys=True, indent=2) + "\n").encode("utf-8")
    filename = f"archive-deployment-backup-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
    )
