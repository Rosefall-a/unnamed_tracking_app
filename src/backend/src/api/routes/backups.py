"""Settings > Admin > Backups: the automatic whole-database backup schedule,
the backups themselves, and leftover files that nothing in the database points
at any more. Only an admin can delete any of these, one at a time, by hand."""

from __future__ import annotations

import asyncio
import re
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_admin
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import get_db
from src.features.backup import scheduler, snapshot

router = APIRouter(
    prefix="/api/settings/backups", tags=["settings"], dependencies=[Depends(get_current_admin)]
)

_GAMES_DATA_ROOT = Path("/data/users")
DELETED_ACCOUNTS_ROOT = snapshot.DELETED_ACCOUNTS_ROOT
# before whole-database backups, each account got its own folder of backups here;
# nothing writes, rotates or restores those any more
_OLD_BACKUPS_ROOT = snapshot.BACKUP_ROOT
_UUID_NAME = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class BackupSettingsUpdate(BaseModel):
    enabled: bool | None = None
    interval_minutes: int | None = None
    keep: int | None = None
    include_files: bool | None = None
    files_keep: int | None = None


def _folder_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return total


async def _describe(db: AsyncSession) -> dict[str, Any]:
    row = await scheduler.get_setting(db)
    return {
        "enabled": row.enabled,
        "interval_minutes": row.interval_minutes,
        "min_interval_minutes": scheduler.MIN_INTERVAL_MINUTES,
        "max_interval_minutes": scheduler.MAX_INTERVAL_MINUTES,
        "keep": scheduler.keep_count(row),
        "max_keep": scheduler.MAX_KEEP,
        "last_run_at": row.last_run_at,
        "last_result": row.last_result or {},
        "running": scheduler.is_running(),
        "folder": str(snapshot.DATABASE_DIR),
        "include_files": scheduler.includes_files(row),
        "files_keep": scheduler.files_keep(row),
        "max_files_keep": scheduler.MAX_FILES_KEEP,
        "storage": await asyncio.to_thread(snapshot.storage_report),
    }


@router.get("")
async def get_backups(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    out = await _describe(db)
    await db.commit()
    out["backups"] = [
        b.__dict__ for b in await asyncio.to_thread(snapshot.list_backups, snapshot.DATABASE_DIR)
    ]
    return out


@router.put("")
async def update_backup_settings(
    payload: BackupSettingsUpdate, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await scheduler.get_setting(db)
    if payload.interval_minutes is not None:
        if not (
            scheduler.MIN_INTERVAL_MINUTES
            <= payload.interval_minutes
            <= scheduler.MAX_INTERVAL_MINUTES
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Backups can run from every hour to every 30 days.",
            )
        row.interval_minutes = payload.interval_minutes
    if payload.keep is not None:
        if not 0 <= payload.keep <= scheduler.MAX_KEEP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Keep between 0 (every backup) and {scheduler.MAX_KEEP}.",
            )
        row.options = {**(row.options or {}), "keep": payload.keep}
    if payload.files_keep is not None:
        if not 1 <= payload.files_keep <= scheduler.MAX_FILES_KEEP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Keep files with between 1 and {scheduler.MAX_FILES_KEEP} backups.",
            )
        row.options = {**(row.options or {}), "files_keep": payload.files_keep}
    if payload.include_files is not None:
        row.options = {**(row.options or {}), "include_files": payload.include_files}
    if payload.enabled is not None:
        row.enabled = payload.enabled
    await db.commit()
    return await _describe(db)


@router.post("/run")
async def run_backups_now() -> dict[str, bool]:
    return {"started": scheduler.start_now()}


@router.get("/database/{name}", response_class=FileResponse)
async def download_database_backup(name: str) -> FileResponse:
    path = snapshot.DATABASE_DIR / name
    if not snapshot.BACKUP_NAME.match(name) or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    return FileResponse(path, filename=name, media_type="application/octet-stream")


@router.get("/database/{name}/files", response_class=FileResponse)
async def download_files_copy(name: str) -> FileResponse:
    path = snapshot.files_path(snapshot.DATABASE_DIR, name)
    if not snapshot.BACKUP_NAME.match(name) or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No files copy.")
    return FileResponse(path, filename=path.name, media_type="application/x-tar")


@router.delete("/database/{name}")
async def delete_database_backup(name: str) -> dict[str, str]:
    if not await asyncio.to_thread(snapshot.delete_backup, snapshot.DATABASE_DIR, name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    return {"status": "deleted"}


# leftovers --------------------------------------------------------------


async def _leftovers(db: AsyncSession) -> list[dict[str, Any]]:
    known_games = {str(g) for g in (await db.execute(select(Game.id))).scalars()}
    known_users = {str(u) for u in (await db.execute(select(User.id))).scalars()}

    def entry(kind: str, name: str, label: str, folder: Path) -> dict[str, Any]:
        return {
            "kind": kind,
            "name": name,
            "label": label,
            "path": str(folder),
            "bytes": _folder_size(folder),
            "modified_at": int(folder.stat().st_mtime),
        }

    def scan() -> list[dict[str, Any]]:
        out = []
        trash = _GAMES_DATA_ROOT / "_trash"
        if trash.is_dir():
            for folder in trash.iterdir():
                if (
                    folder.is_dir()
                    and _UUID_NAME.match(folder.name)
                    and folder.name not in known_games
                ):
                    out.append(
                        entry(
                            "game_trash",
                            folder.name,
                            "Files of a game deleted from the trash",
                            folder,
                        )
                    )
        # accounts deleted before their files were set aside left them in place
        for root in snapshot.USER_FILE_ROOTS:
            if not root.is_dir():
                continue
            for folder in root.iterdir():
                if (
                    folder.is_dir()
                    and _UUID_NAME.match(folder.name)
                    and folder.name not in known_users
                ):
                    out.append(
                        entry(
                            "account_files",
                            f"{root.name}-{folder.name}",
                            "Files of an account that no longer exists",
                            folder,
                        )
                    )
        if DELETED_ACCOUNTS_ROOT.is_dir():
            for folder in DELETED_ACCOUNTS_ROOT.iterdir():
                if folder.is_dir():
                    out.append(
                        entry("deleted_account", folder.name, "Files of a deleted account", folder)
                    )
        if _OLD_BACKUPS_ROOT.is_dir():
            for folder in _OLD_BACKUPS_ROOT.iterdir():
                if folder.is_dir() and _UUID_NAME.match(folder.name):
                    whose = "an account" if folder.name in known_users else "a deleted account"
                    out.append(
                        entry(
                            "old_backups",
                            folder.name,
                            f"Older backups of {whose}, from before whole-database backups",
                            folder,
                        )
                    )
        return out

    return await asyncio.to_thread(scan)


@router.get("/leftovers")
async def list_leftovers(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    return await _leftovers(db)


@router.delete("/leftovers/{kind}")
async def delete_leftovers_of_kind(kind: str, db: AsyncSession = Depends(get_db)) -> dict[str, int]:
    """Every leftover of one kind at once, such as hundreds of folders of
    accounts that no longer exist. Only what the list offers right now goes."""
    matches = [item for item in await _leftovers(db) if item["kind"] == kind]
    for item in matches:
        await asyncio.to_thread(shutil.rmtree, Path(item["path"]))
    return {"deleted": len(matches)}


@router.delete("/leftovers/{kind}/{name}")
async def delete_leftover(
    kind: str, name: str, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    # only something the list above offers can be deleted, checked again here
    match = next(
        (item for item in await _leftovers(db) if item["kind"] == kind and item["name"] == name),
        None,
    )
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    await asyncio.to_thread(shutil.rmtree, Path(match["path"]))
    return {"status": "deleted"}
