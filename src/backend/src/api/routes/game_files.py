"""Game files routes, composed by the games router."""

import time
from pathlib import Path
from typing import Literal, cast
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.utils.games import (
    _DATA_ROOT,
    _get_game_or_404,
)
from src.core.app_integrations import get_max_upload_size_mb, get_upload_limits_mb
from src.core.auth import get_current_user
from src.database.models.game_file_item import GameFileItem
from src.database.models.user import User
from src.database.session import get_db
from src.features.trash.media_trash import move_media_file_to_trash, restore_media_file_from_trash
from src.features.trash.sweep import RETENTION_SECONDS
from src.helpers.media import list_media, save_media_bytes
from src.helpers.media_dates import detect_date

_FILES_DEFAULT = File(None, alias="files")


_FILE_DEFAULT = File(None, alias="file")


_DB_DEPENDENCY = Depends(get_db)


_CURRENT_USER_DEPENDENCY = Depends(get_current_user)


_FILE_MODIFIED_FORM = Form(None)


router = APIRouter()

GameFileKind = Literal["doc", "modpack"]
# "save" and "world_save" moved to game_archives.py — named, versioned
# archives instead of an anonymous single flat file each

_GAME_FILE_SUBDIRS: dict[GameFileKind, str] = {
    "doc": "docs",
    "modpack": "modpacks",
}


def _game_file_subdir(kind: GameFileKind) -> str:
    return _GAME_FILE_SUBDIRS[kind]


async def _sync_game_file_items(game_id: UUID, game_dir: Path, db: AsyncSession) -> None:
    """Docs/modpacks used to be tracked only on disk, with no DB row at
    all — this backfills a row (created_at from the file's mtime) for
    anything already sitting in the active folder that doesn't have one
    yet, so existing files from before this migration still show up
    without a one-time manual migration script (same approach as
    media.py's _sync_inbox_items)."""
    existing = await db.execute(
        select(GameFileItem.kind, GameFileItem.filename).where(
            GameFileItem.game_id == game_id, GameFileItem.deleted_at.is_(None)
        )
    )
    known = set(existing.all())
    added = False
    for kind in ("doc", "modpack"):
        for filename in list_media(game_dir / _game_file_subdir(kind)):  # type: ignore[arg-type]
            if (kind, filename) in known:
                continue
            path = game_dir / _game_file_subdir(kind) / filename  # type: ignore[arg-type]
            try:
                mtime = int(path.stat().st_mtime)
            except OSError:
                mtime = int(time.time())
            db.add(GameFileItem(game_id=game_id, kind=kind, filename=filename, created_at=mtime))
            added = True
    if added:
        await db.commit()


def _game_file_to_dict(item: GameFileItem, game_id: UUID, game_dir: Path) -> dict:
    path = game_dir / _game_file_subdir(cast(GameFileKind, item.kind)) / item.filename
    return {
        "id": str(item.id),
        "filename": item.filename,
        "kind": item.kind,
        "size": path.stat().st_size if path.is_file() else 0,
        "url": f"/api/game/{game_id}/files/{item.kind}/{item.filename}",
        "created_at": item.created_at,
        "title": item.title,
        "note": item.note,
        "tags": item.tags,
        "taken_at": item.taken_at,
        "taken_source": item.taken_source,
    }


# Keep the established workflow and public parameters together.
# pylint: disable=duplicate-code,too-many-locals,too-many-positional-arguments
@router.post("/{game_id}/files/{kind}")
async def upload_game_files(
    game_id: UUID,
    kind: GameFileKind,
    files: list[UploadFile] | None = _FILES_DEFAULT,
    file: UploadFile | None = _FILE_DEFAULT,
    last_modified: list[int] | None = _FILE_MODIFIED_FORM,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    """Generic file attachments for a game — docs/manuals and modpacks can
    be almost any format, so unlike screenshots/clips there's no
    content-type validation, just a size cap."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    if not game.folder_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Game folder_location is missing."
        )

    # a modpack zip is routinely hundreds of MB to a few GB — far past a
    # doc-sized limit
    limit_mb = (
        (await get_upload_limits_mb(db))["max_world_save_size_mb"]
        if kind == "modpack"
        else await get_max_upload_size_mb(db)
    )
    max_bytes = limit_mb * 1024 * 1024
    # Accept both the current plural field used by the frontend and the
    # legacy/single-file field used by older clients.
    uploads = list(files or [])
    if file is not None:
        uploads.append(file)
    if not uploads:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required.",
        )
    results: list[dict] = []
    for index, upload in enumerate(uploads):
        data = await upload.read()
        if len(data) > max_bytes:
            results.append(
                {
                    "filename": upload.filename,
                    "status": "rejected",
                    "reason": f"Larger than {limit_mb} MB.",
                }
            )
            continue
        dest_dir = (
            _DATA_ROOT
            / str(game.user_id)
            / "games"
            / game.folder_location
            / _game_file_subdir(kind)
        )
        saved_path = save_media_bytes(data, dest_dir, upload.filename or "file")
        taken_at, taken_source = detect_date(
            data,
            upload.filename or "",
            "doc",
            last_modified[index] if last_modified and index < len(last_modified) else None,
        )
        db.add(
            GameFileItem(
                game_id=game_id,
                kind=kind,
                filename=saved_path.name,
                taken_at=taken_at,
                taken_source=taken_source,
            )
        )
        results.append({"filename": saved_path.name, "status": "saved", "size": len(data)})

    await db.commit()
    return {"results": results}


# pylint: enable=duplicate-code,too-many-locals,too-many-positional-arguments


@router.get("/{game_id}/files/{kind}")
async def list_game_files(
    game_id: UUID,
    kind: GameFileKind,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    game = await _get_game_or_404(game_id, db, current_user.id)
    if not game.folder_location:
        return {"files": []}
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / game.folder_location
    await _sync_game_file_items(game_id, game_dir, db)
    result = await db.execute(
        select(GameFileItem)
        .where(
            GameFileItem.game_id == game_id,
            GameFileItem.kind == kind,
            GameFileItem.deleted_at.is_(None),
        )
        .order_by(GameFileItem.filename)
    )
    return {
        "files": [_game_file_to_dict(item, game_id, game_dir) for item in result.scalars().all()]
    }


class GameFileUpdate(BaseModel):
    __module__ = "src.api.routes.games"
    title: str | None = Field(default=None, max_length=200)
    note: str | None = None
    tags: list[str] | None = None
    taken_at: int | None = None
    taken_source: Literal["manual", "achievement"] | None = None


# Keep the established workflow and public parameters together.
# pylint: disable=duplicate-code,too-many-positional-arguments
@router.patch("/{game_id}/files/{kind}/by-id/{item_id}")
async def update_game_file(
    game_id: UUID,
    kind: GameFileKind,
    item_id: UUID,
    payload: GameFileUpdate,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    game = await _get_game_or_404(game_id, db, current_user.id)
    item = await db.scalar(
        select(GameFileItem).where(
            GameFileItem.id == item_id,
            GameFileItem.game_id == game_id,
            GameFileItem.kind == kind,
            GameFileItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "title" in changes and changes["title"] is not None:
        changes["title"] = changes["title"].strip() or None
    source = changes.pop("taken_source", None)
    for field, value in changes.items():
        setattr(item, field, value)
    if "taken_at" in changes:
        item.taken_source = (source or "manual") if changes["taken_at"] is not None else None
    await db.commit()
    await db.refresh(item)
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    return _game_file_to_dict(item, game_id, game_dir)


# pylint: enable=duplicate-code,too-many-positional-arguments


@router.get("/{game_id}/files/{kind}/trash")
async def list_game_file_trash(
    game_id: UUID,
    kind: GameFileKind,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    await _get_game_or_404(game_id, db, current_user.id)
    result = await db.execute(
        select(GameFileItem)
        .where(
            GameFileItem.game_id == game_id,
            GameFileItem.kind == kind,
            GameFileItem.deleted_at.is_not(None),
        )
        .order_by(GameFileItem.deleted_at.desc())
    )
    files = []
    for item in result.scalars().all():
        assert item.deleted_at is not None  # guaranteed by the deleted_at.is_not(None) filter above
        files.append(
            {
                "id": str(item.id),
                "filename": item.filename,
                "deleted_at": item.deleted_at,
                "purge_at": item.deleted_at + RETENTION_SECONDS,
            }
        )
    return {"files": files}


# Parallel routes/models intentionally share this shape.
# pylint: disable=duplicate-code
@router.get("/{game_id}/files/{kind}/{filename}", response_class=FileResponse)
async def get_game_file(
    game_id: UUID,
    kind: GameFileKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> FileResponse:
    game = await _get_game_or_404(game_id, db, current_user.id)
    path = (
        _DATA_ROOT
        / str(game.user_id)
        / "games"
        / (game.folder_location or "")
        / _game_file_subdir(kind)
        / Path(filename).name
    )
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    # arbitrary user files (saves/docs) should download, not attempt to
    # render inline the way an image/video screenshot asset does — the
    # random 8-char prefix save_media_bytes adds to dedupe filenames is
    # stripped back off for the name the browser actually saves it as
    original_name = Path(filename).name.split("_", 1)[-1]
    return FileResponse(path, filename=original_name, media_type="application/octet-stream")


# pylint: enable=duplicate-code


@router.delete("/{game_id}/files/{kind}/{filename}")
async def delete_game_file(
    game_id: UUID,
    kind: GameFileKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    """Soft-delete: moves the file to trash and marks its row deleted
    rather than removing it — restorable for 7 days, same as every other
    delete path in the app (features/trash/sweep.py does the eventual
    real deletion)."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    await _sync_game_file_items(game_id, game_dir, db)
    name = Path(filename).name
    item = await db.scalar(
        select(GameFileItem).where(
            GameFileItem.game_id == game_id,
            GameFileItem.kind == kind,
            GameFileItem.filename == name,
            GameFileItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    path = game_dir / _game_file_subdir(kind) / name
    move_media_file_to_trash(path, game_dir, kind)
    item.deleted_at = int(time.time())
    await db.commit()
    return {"status": "trashed", "filename": name}


@router.post("/{game_id}/files/{kind}/{filename}/restore")
async def restore_game_file(
    game_id: UUID,
    kind: GameFileKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    game = await _get_game_or_404(game_id, db, current_user.id)
    name = Path(filename).name
    item = await db.scalar(
        select(GameFileItem).where(
            GameFileItem.game_id == game_id,
            GameFileItem.kind == kind,
            GameFileItem.filename == name,
            GameFileItem.deleted_at.is_not(None),
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted file not found.")
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    restore_media_file_from_trash(name, game_dir / _game_file_subdir(kind), game_dir, kind)
    item.deleted_at = None
    await db.commit()
    return {"status": "restored", "filename": name}
