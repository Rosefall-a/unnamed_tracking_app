"""Administrative deployment backup export/import.

Backups are stored server-side by default. Direct browser downloads are an
explicit opt-in through ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD.

This router intentionally delegates archive construction/restoration to
core.application_backup so the setup flow and Settings page use one format.
SMTP fields are excluded by that core service.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.application_backup import (
    application_backup_path,
    create_application_backup_file,
    restore_application_backup,
)
from src.core.auth import get_current_admin
from src.core.config import settings
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(
    prefix="/api/settings/backup",
    tags=["settings"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/status")
async def backup_status(admin: User = Depends(get_current_admin)) -> dict[str, bool | str]:
    del admin
    path = application_backup_path()
    return {
        "available": path.is_file(),
        "download_enabled": bool(settings.ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD),
        "path": str(path),
    }


@router.post("/export", response_model=None)
async def export_backup(
    password: str = Form(..., min_length=12, max_length=256),
    include_users: bool = Form(False),
    include_sessions: bool = Form(False),
    download: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> Response | dict[str, bool | str]:
    del admin
    if download and not settings.ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD:
        raise HTTPException(403, "Direct deployment-secret downloads are disabled.")

    if include_sessions and not include_users:
        raise HTTPException(400, "Sessions can only be included when users are included.")

    body = await create_application_backup_file(
        db,
        password,
        include_users=include_users,
        include_sessions=include_sessions,
        include_application_settings=True,
        include_provider_credentials=True,
        include_oidc_settings=True,
    )

    path = application_backup_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)

    if download:
        return Response(
            content=body,
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="application.json"',
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
            },
        )

    return {"saved": True, "path": str(path), "download_enabled": bool(settings.ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD)}


@router.post("/import")
async def import_backup(
    password: str = Form(..., min_length=12, max_length=256),
    backup_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> dict[str, bool]:
    del admin
    raw = await backup_file.read()
    if not raw:
        raise HTTPException(400, "The deployment backup file is empty.")
    try:
        return await restore_application_backup(db, raw, password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
