"""Library export/import, a portable JSON snapshot of a user's games, for
backups or moving to a new server. Scoped to game data only (folder assets,
screenshots, saves, and bounties aren't included in this pass, those are
each a bigger, separate lift)."""

import time

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.games import _derive_sort_title, _validate_game_relationship
from src.api.schemas.game import GameCreate, GameRead
from src.core.auth import get_current_user
from src.database.models.game import Game, GameLink
from src.database.models.user import User
from src.database.session import get_db
from src.features.backup.scheduler import (
    BACKUP_INTERVAL_SECONDS,
    BACKUPS_TO_KEEP_PER_USER,
    _BACKUP_ROOT,
)
from src.helpers.save_game_asset import create_game_folder

router = APIRouter(prefix="/api", tags=["export"], dependencies=[Depends(get_current_user)])


class LibraryExport(BaseModel):
    format_version: int = 1
    exported_at: int
    game_count: int
    games: list[GameRead]


@router.get("/export/library", response_model=LibraryExport)
async def export_library(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LibraryExport:
    stmt = (
        select(Game)
        .where(Game.user_id == current_user.id, Game.deleted_at.is_(None))
        .order_by(Game.sort_title)
    )
    result = await db.execute(stmt)
    games = list(result.scalars().all())
    return LibraryExport(exported_at=int(time.time()), game_count=len(games), games=games)  # type: ignore[arg-type]


class BackupStatus(BaseModel):
    enabled: bool = True
    interval_hours: int
    backups_kept: int
    last_backup_at: int | None
    backup_count: int


@router.get("/export/backup-status", response_model=BackupStatus)
async def backup_status(current_user: User = Depends(get_current_user)) -> BackupStatus:
    user_dir = _BACKUP_ROOT / str(current_user.id)
    files = sorted(user_dir.glob("backup-*.json"), reverse=True) if user_dir.is_dir() else []
    last_at = None
    if files:
        # filenames are "backup-<epoch>.json", reading the timestamp back
        # out of the name avoids a second stat() call for the same info
        try:
            last_at = int(files[0].stem.split("-")[1])
        except (IndexError, ValueError):
            last_at = int(files[0].stat().st_mtime)
    return BackupStatus(
        interval_hours=BACKUP_INTERVAL_SECONDS // 3600,
        backups_kept=BACKUPS_TO_KEEP_PER_USER,
        last_backup_at=last_at,
        backup_count=len(files),
    )


class ImportResult(BaseModel):
    created: int
    skipped: int
    errors: list[str]


async def _available_folder_location(folder_name: str, db: AsyncSession) -> str:
    """folder_location is unique server-wide, pick the first free
    'name', 'name-2', 'name-3'... instead of failing the whole import over
    one collision (importing back onto the same server being the most
    common way this collision actually happens)."""
    candidate = folder_name
    suffix = 2
    while True:
        stmt = select(Game.id).where(Game.folder_location == candidate, Game.deleted_at.is_(None))
        if not (await db.execute(stmt)).scalar_one_or_none():
            return candidate
        candidate = f"{folder_name}-{suffix}"
        suffix += 1


@router.post("/import/library", response_model=ImportResult, status_code=status.HTTP_200_OK)
async def import_library(
    payload: list[GameCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportResult:
    created = 0
    skipped = 0
    errors: list[str] = []

    for entry in payload:
        try:
            data = entry.model_dump()
            data["user_id"] = current_user.id
            data["folder_location"] = await _available_folder_location(data["folder_location"], db)
            if not data.get("sort_title"):
                data["sort_title"] = _derive_sort_title(data["title"])

            # a parent referenced by id from the *exporting* server almost
            # certainly doesn't exist as that same id here, importing the
            # relationship would either fail loudly or silently point at a
            # stranger's game, so it's dropped rather than guessed at
            try:
                await _validate_game_relationship(
                    data.get("parent_game_id"), data.get("relationship_type"), db, current_user.id
                )
            except Exception:
                data["parent_game_id"] = None
                data["relationship_type"] = None

            link_rows = [
                GameLink(label=link["label"], url=link["url"]) for link in data.pop("links", [])
            ]
            game = Game(**data)
            game.links = link_rows
            db.add(game)
            await db.commit()
            await db.refresh(game)
            create_game_folder(current_user.id, game.folder_location)
            created += 1
        except IntegrityError as exc:
            await db.rollback()
            skipped += 1
            errors.append(f"{entry.title}: {exc.orig if exc.orig else 'duplicate or invalid data'}")
        except Exception as exc:  # noqa: BLE001, one bad row shouldn't abort the whole import
            await db.rollback()
            skipped += 1
            errors.append(f"{entry.title}: {exc}")

    return ImportResult(created=created, skipped=skipped, errors=errors[:20])
