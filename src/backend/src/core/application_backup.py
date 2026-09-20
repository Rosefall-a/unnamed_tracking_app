"""Bootstrap and restore password-protected deployment settings."""

from __future__ import annotations

import base64
import json
import os
import time
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
from src.core.fernet_key import persistent_fernet_key, restore_persistent_fernet_key
from src.database.models.oidc_settings import OidcSettings
from src.database.models.app_integration_settings import AppIntegrationSettings
from src.database.models.auth import UserApiKey, UserSession
from src.database.models.user import User

KDF_ITERATIONS = 600_000
SALT_BYTES = 16
# Set only when an APPLICATION_JSON_PASSWORD startup restore has completed.
# The notice is intentionally process-local and is consumed by the first
# authenticated administrator who reaches the application after startup.
_automatic_restore_completed = False

def mark_automatic_restore_completed() -> None:
    global _automatic_restore_completed
    _automatic_restore_completed = True

def consume_automatic_restore_notice() -> bool:
    global _automatic_restore_completed
    if not _automatic_restore_completed:
        return False
    _automatic_restore_completed = False
    return True

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

    if backup.get("format") != "archive-deployment-backup" or backup.get("format_version") not in {
        1,
        2,
        3,
    }:
        raise ValueError("Unsupported application settings backup format.")
    if not isinstance(backup.get("fernet_keys"), list):
        raise ValueError("The application settings backup is missing its Fernet keys.")
    return backup


def preview_application_backup(raw: bytes, password: str) -> dict[str, Any]:
    """Return setup-wizard values without mutating the database."""
    backup = decode_application_backup(raw, password)
    restore_key = _restore_key(backup)
    options = backup.get("options") or {}
    app_payload = backup.get("app_integration_settings") or {}
    oidc_payload = backup.get("oidc_settings") or {}

    def decrypt(value: Any) -> str | None:
        if not value:
            return None
        try:
            return Fernet(restore_key.encode()).decrypt(str(value).encode()).decode()
        except InvalidToken:
            return str(value)

    oidc: dict[str, Any] = {}
    if options.get("include_oidc_settings", True) and isinstance(oidc_payload, dict):
        oidc = {
            key: value for key, value in oidc_payload.items() if key not in {"id", "updated_at"}
        }
        if oidc.get("client_secret"):
            oidc["client_secret"] = decrypt(oidc["client_secret"])
        if oidc.get("providers_json"):
            try:
                providers = json.loads(str(oidc["providers_json"]))
            except (TypeError, ValueError):
                providers = []
            if isinstance(providers, list):
                for provider in providers:
                    if isinstance(provider, dict) and provider.get("client_secret"):
                        provider["client_secret"] = decrypt(provider["client_secret"])
                oidc["providers_json"] = json.dumps(providers)

    smtp_fields = {
        "smtp_enabled",
        "smtp_host",
        "smtp_port",
        "smtp_username",
        "smtp_password",
        "smtp_use_tls",
        "smtp_use_ssl",
        "smtp_from_email",
        "smtp_from_name",
    }
    smtp = {key: app_payload.get(key) for key in smtp_fields if key in app_payload}
    if smtp.get("smtp_password"):
        smtp["smtp_password"] = decrypt(smtp["smtp_password"])

    return {
        "options": options,
        "has_users": bool(options.get("include_users") and backup.get("users")),
        "has_sessions": bool(options.get("include_sessions") and backup.get("user_sessions")),
        "oidc": oidc,
        "smtp": smtp,
    }


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
    encrypted_secrets = bool(backup.get("secret_values_encrypted", False))
    options = backup.get("options") or {}
    include_application_settings = options.get("include_application_settings", True)
    include_oidc_settings = options.get("include_oidc_settings", True)
    app_payload = backup.get("app_integration_settings")
    oidc_payload = backup.get("oidc_settings")
    if include_application_settings and not isinstance(app_payload, dict):
        raise ValueError(
            "The application settings backup is missing its application settings section."
        )
    if include_oidc_settings and not isinstance(oidc_payload, dict):
        raise ValueError("The application settings backup is missing its OIDC settings section.")

    restore_persistent_fernet_key(restore_key)
    settings.SECRET_KEY = restore_key
    _fernet.cache_clear()

    if include_application_settings:
        app = await db.scalar(select(AppIntegrationSettings).limit(1))
        if app is None:
            app = AppIntegrationSettings()
            db.add(app)
            await db.flush()
        app_columns = {column.name for column in app.__table__.columns}
        for field, value in (app_payload or {}).items():
            if field not in app_columns or field in {"id", "updated_at"}:
                continue
            column = app.__table__.columns[field]
            if value is None and not column.nullable:
                continue
            setattr(
                app,
                field,
                (str(value) if encrypted_secrets else encrypt_secret(str(value)))
                if field in SECRET_FIELDS and value
                else value,
            )

    if include_oidc_settings:
        oidc = await db.scalar(select(OidcSettings).limit(1))
        if oidc is None:
            oidc = OidcSettings()
            db.add(oidc)
        oidc_columns = {column.name for column in oidc.__table__.columns}
        for field, value in (oidc_payload or {}).items():
            if field not in oidc_columns or field in {"id", "updated_at"}:
                continue
            column = oidc.__table__.columns[field]
            if value is None and not column.nullable:
                continue
            if field == "client_secret":
                value = (
                    str(value)
                    if encrypted_secrets
                    else (encrypt_secret(str(value)) if value else None)
                )
            elif field == "providers_json" and value:
                try:
                    providers = json.loads(str(value))
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        "The OIDC provider configuration in the backup is invalid."
                    ) from exc
                if not isinstance(providers, list):
                    raise ValueError("The OIDC provider configuration in the backup is invalid.")
                normalized = []
                for provider in providers:
                    if not isinstance(provider, dict):
                        raise ValueError(
                            "The OIDC provider configuration in the backup is invalid."
                        )
                    item = dict(provider)
                    if item.get("client_secret") and not encrypted_secrets:
                        item["client_secret"] = encrypt_secret(str(item["client_secret"]))
                    normalized.append(item)
                value = json.dumps(normalized)
            setattr(oidc, field, value)

    options = backup.get("options") or {}
    if options.get("include_users"):
        user_payload = backup.get("users")
        if not isinstance(user_payload, list):
            raise ValueError("The full installation backup is missing its users.")
        allowed = {column.name for column in User.__table__.columns}
        for item in user_payload:
            if not isinstance(item, dict):
                raise ValueError("The full installation backup contains an invalid user.")
            values = {key: value for key, value in item.items() if key in allowed}
            db.add(User(**values))

        # UserApiKey and UserSession have database-level foreign keys to users.
        # The User model does not declare ORM relationships, so SQLAlchemy cannot
        # infer that dependency when ordering INSERTs. Flush the users first so
        # PostgreSQL can satisfy those foreign keys during a full-install restore.
        await db.flush()

        key_payload = backup.get("user_api_keys", [])
        if not isinstance(key_payload, list):
            raise ValueError("The full installation backup contains invalid API keys.")
        allowed = {column.name for column in UserApiKey.__table__.columns}
        for item in key_payload:
            if not isinstance(item, dict):
                raise ValueError("The full installation backup contains an invalid API key.")
            values = {key: value for key, value in item.items() if key in allowed}
            db.add(UserApiKey(**values))

    if options.get("include_sessions"):
        if not options.get("include_users"):
            raise ValueError("Sessions can only be restored when users are included.")
        session_payload = backup.get("user_sessions", [])
        if not isinstance(session_payload, list):
            raise ValueError("The full installation backup contains invalid sessions.")
        allowed = {column.name for column in UserSession.__table__.columns}
        for item in session_payload:
            if not isinstance(item, dict):
                raise ValueError("The full installation backup contains an invalid session.")
            values = {key: value for key, value in item.items() if key in allowed}
            db.add(UserSession(**values))

    await db.commit()
    return {
        "application": True,
        "oidc": True,
        "encryption": True,
        "users": bool(options.get("include_users")),
        "sessions": bool(options.get("include_sessions")),
    }


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


def _model_payload(row: Any, *, exclude: set[str] | None = None) -> dict[str, Any]:
    excluded = exclude or set()
    result: dict[str, Any] = {}
    for column in row.__table__.columns:
        name = column.name
        if name in excluded:
            continue
        value = getattr(row, name)
        if hasattr(value, "hex"):
            value = str(value)
        result[name] = value
    return result


async def build_application_backup(
    db: AsyncSession,
    *,
    include_users: bool = False,
    include_sessions: bool = False,
    include_application_settings: bool = True,
    include_provider_credentials: bool = True,
    include_oidc_settings: bool = True,
    include_smtp_settings: bool = False,
) -> dict[str, Any]:
    """Build the encrypted deployment archive payload.

    User credentials are kept in their existing encrypted-at-rest form and the
    installation Fernet key is included, so restoring the archive preserves
    access to those credentials without placing plaintext secrets in the JSON
    envelope.
    """
    app = await db.scalar(select(AppIntegrationSettings).limit(1))
    if app is None:
        app = AppIntegrationSettings()
        db.add(app)
        await db.flush()
    oidc = await db.scalar(select(OidcSettings).limit(1))
    if oidc is None:
        oidc = OidcSettings()
        db.add(oidc)
        await db.flush()

    payload: dict[str, Any] = {
        "format": "archive-deployment-backup",
        "format_version": 3,
        "secret_values_encrypted": True,
        "exported_at": int(time.time()),
        "fernet_keys": [persistent_fernet_key(), persistent_fernet_key()],
        "options": {
            "include_users": include_users,
            "include_sessions": include_sessions,
            "include_application_settings": include_application_settings,
            "include_provider_credentials": include_provider_credentials,
            "include_oidc_settings": include_oidc_settings,
            "include_smtp_settings": include_smtp_settings,
        },
    }
    if include_application_settings:
        app_payload = _model_payload(app, exclude={"id", "updated_at"})
        if not include_provider_credentials:
            app_payload = {
                k: v
                for k, v in app_payload.items()
                if k not in SECRET_FIELDS
                and k
                not in {
                    "igdb_client_id",
                    "screenscraper_ssid",
                    "screenscraper_devid",
                    "xbox_client_id",
                }
            }
        if not include_smtp_settings:
            app_payload = {k: v for k, v in app_payload.items() if not k.startswith("smtp_")}
        payload["app_integration_settings"] = app_payload
    if include_oidc_settings:
        payload["oidc_settings"] = _model_payload(oidc, exclude={"id", "updated_at"})

    if include_users:
        users = (await db.execute(select(User).order_by(User.username))).scalars().all()
        api_keys = (await db.execute(select(UserApiKey))).scalars().all()
        payload["users"] = [_model_payload(user) for user in users]
        payload["user_api_keys"] = [_model_payload(key) for key in api_keys]

    if include_sessions:
        sessions = (
            (
                await db.execute(
                    select(UserSession).where(
                        UserSession.expires_at > int(__import__("time").time())
                    )
                )
            )
            .scalars()
            .all()
        )
        payload["user_sessions"] = [_model_payload(session) for session in sessions]

    return payload


def encrypt_application_backup(backup: dict[str, Any], password: str) -> bytes:
    if not password or len(password) < 12:
        raise ValueError("The backup password must be at least 12 characters long.")
    salt = os.urandom(SALT_BYTES)
    plaintext = json.dumps(backup, separators=(",", ":"), default=str).encode("utf-8")
    envelope = {
        "format": "archive-deployment-backup-encrypted",
        "format_version": 1,
        "salt": base64.urlsafe_b64encode(salt).decode("ascii"),
        "ciphertext": Fernet(_password_key(password, salt)).encrypt(plaintext).decode("ascii"),
    }
    return json.dumps(envelope, indent=2).encode("utf-8")


async def create_application_backup_file(
    db: AsyncSession,
    password: str,
    *,
    include_users: bool = False,
    include_sessions: bool = False,
    include_application_settings: bool = True,
    include_provider_credentials: bool = True,
    include_oidc_settings: bool = True,
    include_smtp_settings: bool = False,
) -> bytes:
    backup = await build_application_backup(
        db,
        include_users=include_users,
        include_sessions=include_sessions,
        include_application_settings=include_application_settings,
        include_provider_credentials=include_provider_credentials,
        include_oidc_settings=include_oidc_settings,
        include_smtp_settings=include_smtp_settings,
    )
    return encrypt_application_backup(backup, password)
