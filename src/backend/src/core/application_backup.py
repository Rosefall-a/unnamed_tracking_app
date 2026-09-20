"""Bootstrap and restore password-protected deployment settings."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from collections import Counter
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.crypto import _fernet, encrypt_secret
from src.core.data_paths import DATA_ROOT
from src.core.fernet_key import restore_persistent_fernet_key
from src.database.models.oidc_settings import OidcSettings
from src.database.models.app_integration_settings import AppIntegrationSettings

KDF_ITERATIONS = 600_000
SALT_BYTES = 16
SECRET_FIELDS = {
    "steamgriddb_api_key",
    "retroachievements_api_key",
    "giantbomb_api_key",
    "igdb_client_secret",
    "screenscraper_sspassword",
    "screenscraper_devpassword",
    "xbox_client_secret",
    "smtp_password",
}


def _password_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def decode_application_backup(raw: bytes, password: str) -> dict[str, Any]:
    try:
        envelope = json.loads(raw.decode("utf-8"))
        if envelope.get("format") != "archive-deployment-backup-encrypted":
            raise ValueError("unsupported backup format")
        salt = base64.urlsafe_b64decode(envelope["salt"].encode("ascii"))
        plaintext = Fernet(_password_key(password, salt)).decrypt(
            envelope["ciphertext"].encode("ascii")
        )
        backup = json.loads(plaintext.decode("utf-8"))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, InvalidToken) as exc:
        raise ValueError("The application settings file or password is invalid.") from exc

    if backup.get("format") != "archive-deployment-backup" or backup.get("format_version") not in {1, 2}:
        raise ValueError("Unsupported application settings backup format.")
    if not isinstance(backup.get("fernet_keys"), list):
        raise ValueError("The application settings backup is missing its Fernet keys.")
    return backup


def _restore_key(backup: dict[str, Any]) -> str:
    valid: list[str] = []
    for value in backup["fernet_keys"]:
        if isinstance(value, str):
            try:
                Fernet(value.encode())
                valid.append(value)
            except (ValueError, TypeError):
                pass
    if not valid:
        raise ValueError("The application settings backup contains no valid Fernet key.")
    key, count = Counter(valid).most_common(1)[0]
    if len(valid) >= 2 and count < 2:
        raise ValueError("The application settings backup has conflicting Fernet key copies.")
    return key


async def restore_application_backup(
    db: AsyncSession, raw: bytes, password: str
) -> dict[str, bool]:
    backup = decode_application_backup(raw, password)
    restore_key = _restore_key(backup)
    app_payload = backup.get("app_integration_settings")
    oidc_payload = backup.get("oidc_settings")
    if not isinstance(app_payload, dict) or not isinstance(oidc_payload, dict):
        raise ValueError("The application settings backup is missing its settings sections.")

    restore_persistent_fernet_key(restore_key)
    settings.SECRET_KEY = restore_key
    _fernet.cache_clear()

    app = await db.scalar(select(AppIntegrationSettings).limit(1))
    if app is None:
        app = AppIntegrationSettings()
        db.add(app)
        await db.flush()

    app_columns = {column.name for column in app.__table__.columns}
    for field, value in app_payload.items():
        if field in app_columns and field not in {"id", "updated_at"}:
            setattr(
                app,
                field,
                encrypt_secret(str(value)) if field in SECRET_FIELDS and value else value,
            )

    oidc = await db.scalar(select(OidcSettings).limit(1))
    if oidc is None:
        oidc = OidcSettings()
        db.add(oidc)

    oidc_columns = {column.name for column in oidc.__table__.columns}
    for field, value in oidc_payload.items():
        if field in oidc_columns and field not in {"id", "updated_at"}:
            if field == "client_secret":
                value = encrypt_secret(str(value)) if value else None
            elif field == "providers_json" and value:
                try:
                    providers = json.loads(str(value))
                except (TypeError, ValueError) as exc:
                    raise ValueError("The OIDC provider configuration in the backup is invalid.") from exc
                if not isinstance(providers, list):
                    raise ValueError("The OIDC provider configuration in the backup is invalid.")
                normalized = []
                for provider in providers:
                    if not isinstance(provider, dict):
                        raise ValueError("The OIDC provider configuration in the backup is invalid.")
                    item = dict(provider)
                    if item.get("client_secret"):
                        item["client_secret"] = encrypt_secret(str(item["client_secret"]))
                    normalized.append(item)
                value = json.dumps(normalized)
            setattr(oidc, field, value)

    await db.commit()
    return {"application": True, "oidc": True, "encryption": True}


def application_backup_path() -> Path:
    configured = Path(
        str(getattr(settings, "APPLICATION_JSON_PATH", "") or "").strip()
        or str(DATA_ROOT / "application.json")
    )
    if configured.is_absolute():
        return configured
    return Path.cwd() / configured


def load_application_backup_file(password: str) -> bytes | None:
    path = application_backup_path()
    if not path.is_file():
        fallback = Path.cwd() / "application.json"
        if fallback.is_file():
            path = fallback
        else:
            return None
    return path.read_bytes()
