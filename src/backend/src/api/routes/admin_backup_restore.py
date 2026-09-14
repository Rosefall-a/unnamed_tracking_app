from __future__ import annotations

import json
from collections import Counter
from typing import Any

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.admin_backup import (
    _SECRET_APP_FIELDS,
    _decode_backup,
)
from src.core.auth import get_current_admin
from src.core.config import settings as app_settings
from src.core.crypto import encrypt_secret, _fernet
from src.core.fernet_key import restore_persistent_fernet_key
from src.core.provider_credentials import apply_deployment_provider_credentials
from src.core.runtime_settings import apply_runtime_settings
from src.database.models.auth import UserSession
from src.database.models.oidc_settings import OidcSettings
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(
    prefix="/api/settings/backup",
    tags=["settings"],
    dependencies=[Depends(get_current_admin)],
)

_MIN_PASSWORD_LENGTH = 12


@router.post("/restore")
async def restore_deployment_backup(
    password: str = Form(...),
    backup_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    del admin
    if len(password) < _MIN_PASSWORD_LENGTH or len(password) > 256:
        raise HTTPException(400, "Backup password must be between 12 and 256 characters.")

    backup = _decode_backup(await backup_file.read(), password)
    valid_keys: list[str] = []
    for value in backup["fernet_keys"]:
        if not isinstance(value, str):
            continue
        try:
            Fernet(value.encode())
            valid_keys.append(value)
        except (ValueError, TypeError):
            pass
    if not valid_keys:
        raise HTTPException(400, "Backup does not contain a valid Fernet key.")
    restore_key, count = Counter(valid_keys).most_common(1)[0]
    if len(valid_keys) >= 2 and count < 2:
        raise HTTPException(400, "Backup Fernet key copies do not have a matching majority.")

    app_payload = backup.get("app_integration_settings")
    oidc_payload = backup.get("oidc_settings")
    if not isinstance(app_payload, dict) or not isinstance(oidc_payload, dict):
        raise HTTPException(400, "Backup is missing deployment settings.")

    restore_persistent_fernet_key(restore_key)
    app_settings.SECRET_KEY = restore_key
    _fernet.cache_clear()

    app = await __import__(
        "src.api.routes.settings", fromlist=["get_or_create_app_integration_settings"]
    ).get_or_create_app_integration_settings(db)
    app_columns = {column.name for column in app.__table__.columns}
    for field, value in app_payload.items():
        if field in app_columns and field not in {"id", "updated_at"}:
            setattr(app, field, encrypt_secret(str(value)) if field in _SECRET_APP_FIELDS and value else value)

    oidc = await db.scalar(select(OidcSettings).limit(1))
    if oidc is None:
        oidc = OidcSettings()
        db.add(oidc)
    oidc_columns = {column.name for column in oidc.__table__.columns}
    for field, value in oidc_payload.items():
        if field in oidc_columns and field not in {"id", "updated_at", "providers_json", "client_secret"}:
            setattr(oidc, field, value)
    oidc.client_secret = encrypt_secret(str(oidc_payload["client_secret"])) if oidc_payload.get("client_secret") else None

    try:
        providers = json.loads(oidc_payload.get("providers_json", "[]") or "[]")
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Backup OIDC provider configuration is invalid.") from exc
    if not isinstance(providers, list):
        raise HTTPException(400, "Backup OIDC provider configuration is invalid.")
    for provider in providers:
        if isinstance(provider, dict) and provider.get("client_secret"):
            provider["client_secret"] = encrypt_secret(str(provider["client_secret"]))
    oidc.providers_json = json.dumps(providers)

    await db.execute(delete(UserSession))
    await db.commit()
    apply_runtime_settings(app)
    apply_deployment_provider_credentials(app)
    return {
        "restored": True,
        "sessions_revoked": True,
        "message": "Deployment configuration restored. Users must sign in again; user accounts and library data were not imported.",
    }
