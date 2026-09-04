"""API routes for the media inbox — bulk-uploaded screenshots/clips that
haven't been assigned to a game yet, so they can be uploaded in one big
batch and sorted out afterward instead of one game at a time."""

import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.core.config import settings
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import get_db
from src.helpers.media import MediaKind, classify_media, list_media, media_subdir, save_media_bytes
from src.helpers.save_game_asset import DATA_ROOT as GAMES_DATA_ROOT
from src.helpers.save_game_asset import create_game_folder

router = APIRouter(prefix="/api/media", tags=["media"], dependencies=[Depends(get_current_user)])

_USER_DATA_ROOT = Path("/data/user")


class AssignMediaRequest(BaseModel):
    game_id: UUID


def _inbox_dir(user_id: UUID) -> Path:
    return _USER_DATA_ROOT / str(user_id) / "inbox"


@router.post("/inbox")
async def upload_to_inbox(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, list[dict]]:
    """Bulk upload with no game attached yet — sorted into screenshots/clips
    by file type, to be grouped and assigned to games later."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    results: list[dict] = []
    for file in files:
        kind = classify_media(file.content_type, file.filename or "")
        if kind is None:
            results.append({"filename": file.filename, "status": "rejected", "reason": "Unsupported file type."})
            continue

        data = await file.read()
        if len(data) > max_bytes:
            results.append(
                {"filename": file.filename, "status": "rejected", "reason": f"Larger than {settings.MAX_UPLOAD_SIZE_MB} MB."}
            )
            continue

        dest_dir = _inbox_dir(current_user.id) / media_subdir(kind)
        saved_path = save_media_bytes(data, dest_dir, file.filename or "file")
        results.append({"filename": saved_path.name, "status": "saved", "kind": kind})

    return {"results": results}


@router.get("/inbox")
async def list_inbox(current_user: User = Depends(get_current_user)) -> dict[str, list[dict]]:
    inbox = _inbox_dir(current_user.id)
    media = [
        {"filename": name, "kind": "screenshot", "url": f"/api/media/inbox/screenshot/{name}"}
        for name in list_media(inbox / "screenshots")
    ] + [
        {"filename": name, "kind": "clip", "url": f"/api/media/inbox/clip/{name}"}
        for name in list_media(inbox / "clips")
    ]
    return {"media": media}


@router.get("/inbox/{kind}/{filename}", response_class=FileResponse)
async def get_inbox_media(
    kind: MediaKind,
    filename: str,
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    path = _inbox_dir(current_user.id) / media_subdir(kind) / Path(filename).name
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found.")
    return FileResponse(path)


@router.delete("/inbox/{kind}/{filename}")
async def delete_inbox_media(
    kind: MediaKind,
    filename: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    path = _inbox_dir(current_user.id) / media_subdir(kind) / Path(filename).name
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found.")
    path.unlink()
    return {"status": "deleted", "filename": filename}


@router.post("/inbox/{kind}/{filename}/assign")
async def assign_inbox_media(
    kind: MediaKind,
    filename: str,
    payload: AssignMediaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Move a bulk-uploaded file out of the inbox and into a specific
    game's screenshots/clips folder."""
    source_path = _inbox_dir(current_user.id) / media_subdir(kind) / Path(filename).name
    if not source_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found.")

    game = await db.scalar(
        select(Game).where(Game.id == payload.game_id, Game.user_id == current_user.id)
    )
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    if not game.folder_location:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game folder_location is missing.")

    create_game_folder(game.folder_location)
    dest_dir = GAMES_DATA_ROOT / game.folder_location / media_subdir(kind)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / source_path.name
    shutil.move(str(source_path), str(dest_path))

    return {"status": "assigned", "game_id": str(payload.game_id), "filename": dest_path.name}
