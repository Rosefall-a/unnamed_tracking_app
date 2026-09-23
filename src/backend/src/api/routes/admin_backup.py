"""Administrative deployment backup export/import.

The settings page and first-run setup use the same password-protected archive
format. Exports can optionally persist an application.json copy for bootstrap.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.application_backup import (
    application_backup_path,
    create_application_backup_file,
    restore_application_backup,
)
from src.core.auth import get_current_admin
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
        "download_enabled": True,
        "path": str(path),
    }


@router.post("/export")
async def export_backup(
    password: str = Form(..., min_length=12, max_length=256),
    include_application_settings: bool = Form(True),
    include_provider_credentials: bool = Form(True),
    include_oidc_settings: bool = Form(True),
    include_smtp_settings: bool = Form(False),
    include_users: bool = Form(False),
    include_sessions: bool = Form(False),
    full_installation: bool = Form(False),
    save_to_setup_path: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> Response:
    del admin

    if full_installation:
        include_users = True
        include_sessions = True
    if include_sessions and not include_users:
        raise HTTPException(400, "Active sessions require users to be included.")

    body = await create_application_backup_file(
        db,
        password,
        include_users=include_users,
        include_sessions=include_sessions,
        include_application_settings=include_application_settings,
        include_provider_credentials=include_provider_credentials,
        include_oidc_settings=include_oidc_settings,
        include_smtp_settings=include_smtp_settings,
    )

    if save_to_setup_path:
        path = application_backup_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

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
