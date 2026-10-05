"""Game note API routes."""

import os
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.game_helpers import _game_note_path, _get_game_or_404, _normalize_note_name
from src.core.auth import get_current_user
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter()
_DB_DEPENDENCY = Depends(get_db)
_CURRENT_USER_DEPENDENCY = Depends(get_current_user)
_BODY_DOTDOTDOT = Body(...)

class NoteWrite(BaseModel):
    content: str

class NoteRename(BaseModel):
    new_name: str

@router.post(
    "/{game_id}/notes/{note_name}",
    status_code=status.HTTP_201_CREATED,
)
async def create_game_note(
    game_id: UUID,
    note_name: str,
    payload: NoteWrite = _BODY_DOTDOTDOT,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str | None]:
    """Create a markdown note without replacing an existing note."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    normalized_name = _normalize_note_name(note_name)
    note_path = _game_note_path(game, normalized_name)
    try:
        with note_path.open("x", encoding="utf-8") as note_file:
            note_file.write(payload.content)
    except FileExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "note_already_exists", "message": f'A note titled "{normalized_name}" already exists.'},
        ) from exc
    return {"game_id": str(game_id), "note_name": normalized_name, "path": str(note_path), "status": "saved"}


@router.put(
    "/{game_id}/notes/{note_name}",
)
async def update_game_note(
    game_id: UUID,
    note_name: str,
    payload: NoteWrite = _BODY_DOTDOTDOT,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str | None]:
    """Update an existing markdown note."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    normalized_name = _normalize_note_name(note_name)
    note_path = _game_note_path(game, normalized_name)
    if not note_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Note "{normalized_name}" was not found.')
    note_path.write_text(payload.content, encoding="utf-8")
    return {"game_id": str(game_id), "note_name": normalized_name, "path": str(note_path), "status": "saved"}


@router.patch(
    "/{game_id}/notes/{note_name}/rename",
)
async def rename_game_note(
    game_id: UUID,
    note_name: str,
    payload: NoteRename = _BODY_DOTDOTDOT,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str | None]:
    """Rename a note without replacing the destination or losing its contents."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    source_name = _normalize_note_name(note_name)
    destination_name = _normalize_note_name(payload.new_name)
    source_path = _game_note_path(game, source_name)
    destination_path = _game_note_path(game, destination_name)
    if not source_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Note "{source_name}" was not found.')
    if source_name == destination_name:
        return {"game_id": str(game_id), "note_name": source_name, "path": str(source_path), "status": "saved"}
    try:
        os.link(source_path, destination_path)
    except FileExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "note_already_exists", "message": f'A note titled "{destination_name}" already exists.'},
        ) from exc
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="The note could not be renamed.") from exc
    try:
        source_path.unlink()
    except OSError as exc:
        try:
            destination_path.unlink()
        except OSError:
            pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="The note could not be renamed.") from exc
    return {"game_id": str(game_id), "note_name": destination_name, "path": str(destination_path), "status": "saved"}


@router.get(
    "/{game_id}/notes",
    responses={
        status.HTTP_200_OK: {"description": "List of markdown notes for the game"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
    },
)
async def list_game_notes(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[str]]:
    """Return the markdown note names associated with a game."""
    game = await _get_game_or_404(game_id, db, current_user.id)

    if not game.folder_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game folder_location is missing.",
        )

    notes_dir = _DATA_ROOT / str(game.user_id) / "games" / game.folder_location / "notes"
    if not notes_dir.exists():
        return {"notes": []}

    note_names = sorted(
        path.stem for path in notes_dir.iterdir() if path.is_file() and path.suffix.lower() == ".md"
    )
    return {"notes": note_names}


@router.get(
    "/{game_id}/notes/{note_name}",
    responses={
        status.HTTP_200_OK: {"description": "Markdown note contents"},
        status.HTTP_404_NOT_FOUND: {"description": "Game or note not found"},
    },
)
async def get_game_note(
    game_id: UUID,
    note_name: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> Response:
    """Return the contents of one game note as markdown."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    note_path = _game_note_path(game, note_name)

    if not note_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note '{_normalize_note_name(note_name)}' not found for game {game_id}",
        )

    return Response(
        content=note_path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8"
    )


@router.delete(
    "/{game_id}/notes/{note_name}",
    responses={
        status.HTTP_200_OK: {"description": "Note deleted"},
        status.HTTP_404_NOT_FOUND: {"description": "Game or note not found"},
    },
)
async def delete_game_note(
    game_id: UUID,
    note_name: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    """Delete one markdown note from a game."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    note_path = _game_note_path(game, note_name)

    if not note_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note '{_normalize_note_name(note_name)}' not found for game {game_id}",
        )

    note_path.unlink()
    return {
        "game_id": str(game_id),
        "note_name": _normalize_note_name(note_name),
        "status": "deleted",
    }
