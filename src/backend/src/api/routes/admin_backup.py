"""Password-protected deployment configuration export/import and key rotation."""

from __future__ import annotations

import base64
import json
import secrets
import time
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.settings import get_or_create_app_integration_settings
from src.core.auth import get_current_admin
from src.core.config import settings as app_settings
from src.core.crypto import decrypt_secret, encrypt_secret, _fernet
from src.core.data_paths import DATA_ROOT
from src.core.fernet_key import rotate_persistent_fernet_key
from src.core.provider_credentials import apply_deployment_provider_credentials
from src.database.models.auth import UserSession
from src.database.models.app_integration_settings import AppIntegrationSettings
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
_USER_SECRET_FIELDS = {
    "psn_npsso_token",
    "screenscraper_sspassword",
    "xbox_client_secret",
    "gog_refresh_token",
}


class SecretBackupRequest(BaseModel):
    password: str = Field(min_length=_MIN_PASSWORD_LENGTH, max_length=256)


class KeyRotationRequest(BaseModel):
    confirm: bool


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
    try:
        raw = json.loads(row.providers_json or "[]")
    except (TypeError, ValueError) as exc:
        raise HTTPException(500, "Saved OIDC provider configuration is invalid.") from exc
    if not isinstance(raw, list):
        raise HTTPException(500, "Saved OIDC provider configuration is invalid.")
    providers: list[dict[str, Any]] = []
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
    config_dir = DATA_ROOT / "config"
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
        "format_version": 2,
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
        "format_version": 2,
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


@router.post("/rotate-key")
async def rotate_encryption_key(
    payload: KeyRotationRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    """Rotate the deployment Fernet key and re-encrypt every known secret.

    The old key is retained as decrypt-only material during the transition.
    All server sessions are revoked because the installation's cookie
    namespace is derived from the Fernet key.
    """
    del admin
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Key rotation was not confirmed.")

    old_key, new_key = rotate_persistent_fernet_key()
    old_fernet = Fernet(old_key.encode())
    new_fernet = Fernet(new_key.encode())

    def reencrypt(value: str | None) -> str | None:
        if not value:
            return value
        try:
            plaintext = old_fernet.decrypt(value.encode())
        except InvalidToken as exc:
            raise HTTPException(
                500, "A stored secret could not be decrypted during key rotation."
            ) from exc
        return new_fernet.encrypt(plaintext).decode()

    app = await get_or_create_app_integration_settings(db)
    for field in _SECRET_APP_FIELDS:
        setattr(app, field, reencrypt(getattr(app, field)))

    oidc = await db.scalar(select(OidcSettings).limit(1))
    if oidc:
        oidc.client_secret = reencrypt(oidc.client_secret)
        try:
            providers = json.loads(oidc.providers_json or "[]")
        except (TypeError, ValueError) as exc:
            raise HTTPException(500, "Saved OIDC provider configuration is invalid.") from exc
        if isinstance(providers, list):
            for provider in providers:
                if isinstance(provider, dict) and provider.get("client_secret"):
                    provider["client_secret"] = reencrypt(str(provider["client_secret"]))
            oidc.providers_json = json.dumps(providers)

    users = (await db.scalars(select(User))).all()
    for user in users:
        for field in _USER_SECRET_FIELDS:
            setattr(user, field, reencrypt(getattr(user, field)))

    await db.execute(delete(UserSession))
    await db.commit()

    app_settings.SECRET_KEY = new_key
    _fernet.cache_clear()
    apply_deployment_provider_credentials(app)

    return {
        "rotated": True,
        "sessions_revoked": True,
        "users_required_to_sign_in_again": len(users),
        "message": "Encryption key rotated successfully. The previous key is retained for recovery until the next rotation.",
    }
