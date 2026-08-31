import re
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Import transaction utilities from our database module
from app.database.base import run_transaction 

from app.database.session import get_db
from app.database.models.game import Game, GameStatus
from app.api.schemas.game import GameCreate, GameRead, GameUpdate
from app.helpers.save_game_asset import save_game_asset

router = APIRouter(
    prefix="/api/game",
    tags=["game"],
)

_DATA_ROOT = Path("/data/games")
_NOTE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_LEADING_ARTICLE = re.compile(r"^(a|an|the)\s+", flags=re.IGNORECASE)


class NoteWrite(BaseModel):
    content: str


class AssetKind(str):
    pass


ALLOWED_ASSET_KINDS = {"key_art", "banner", "logo", "icon"}


def _derive_sort_title(title: str) -> str:
    """'The Witcher 3' -> 'witcher 3' so articles don't affect sort order."""
    return _LEADING_ARTICLE.sub("", title).strip().lower()


def _duplicate_folder_error(folder_name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "duplicate_folder_location",
            "field": "folder_location",
            "value": folder_name,
            "message": f"A game with folder_location '{folder_name}' already exists.",
        },
    )


async def _ensure_folder_location_available(
    folder_name: str,
    db: AsyncSession,
    exclude_game_id: UUID | None = None,
) -> None:
    stmt = select(Game.id).where(Game.folder_location == folder_name)
    if exclude_game_id is not None:
        stmt = stmt.where(Game.id != exclude_game_id)

    existing = await db.scalar(stmt)
    if existing is not None:
        raise _duplicate_folder_error(folder_name)


def _normalize_note_name(note_name: str) -> str:
    normalized = note_name.strip()
    if normalized.lower().endswith(".md"):
        normalized = normalized[:-3]

    if not normalized or not _NOTE_NAME_PATTERN.fullmatch(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note name must contain only letters, numbers, underscores, or hyphens and no file extension.",
        )

    return normalized


def _game_note_path(game: Game, note_name: str) -> Path:
    if not game.folder_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game folder_location is missing.",
        )

    note_file_name = f"{_normalize_note_name(note_name)}.md"
    note_dir = _DATA_ROOT / game.folder_location / "notes"
    note_dir.mkdir(parents=True, exist_ok=True)
    return note_dir / note_file_name


async def _get_game_or_404(game_id: UUID, db: AsyncSession) -> Game:
    game = await db.get(Game, game_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )
    return game


@router.post(
    "/{game_id}/assets/{asset_kind}",
    responses={
        status.HTTP_200_OK: {"description": "Image uploaded and resized"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid asset kind or upload"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
    },
)
async def upload_game_asset(
    game_id: UUID,
    asset_kind: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if asset_kind not in ALLOWED_ASSET_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported asset kind '{asset_kind}'. Supported values: {sorted(ALLOWED_ASSET_KINDS)}",
        )

    await _get_game_or_404(game_id, db)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is required.",
        )

    image_bytes = await file.read()
    target_path = await save_game_asset(image_bytes, game_id, asset_kind)

    return {
        "game_id": str(game_id),
        "asset_kind": asset_kind,
        "path": str(target_path),
        "status": "saved",
    }


@router.put(
    "/{game_id}/notes/{note_name}",
    responses={
        status.HTTP_201_CREATED: {"description": "Note created or updated"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid note name"},
    },
)
async def set_game_note(
    game_id: UUID,
    note_name: str,
    payload: NoteWrite = Body(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | None]:
    game = await _get_game_or_404(game_id, db)
    note_path = _game_note_path(game, note_name)
    note_path.write_text(payload.content, encoding="utf-8")

    return {
        "game_id": str(game_id),
        "note_name": _normalize_note_name(note_name),
        "path": str(note_path),
        "status": "saved",
    }


@router.get(
    "/{game_id}/notes",
    responses={
        status.HTTP_200_OK: {"description": "List of markdown notes for the game"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
    },
)
async def list_game_notes(
    game_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[str]]:
    game = await _get_game_or_404(game_id, db)

    if not game.folder_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game folder_location is missing.",
        )

    notes_dir = _DATA_ROOT / game.folder_location / "notes"
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
    db: AsyncSession = Depends(get_db),
) -> Response:
    game = await _get_game_or_404(game_id, db)
    note_path = _game_note_path(game, note_name)

    if not note_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note '{_normalize_note_name(note_name)}' not found for game {game_id}",
        )

    return Response(content=note_path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


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
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    game = await _get_game_or_404(game_id, db)
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


@router.post(
    "/{game_id}/assets/{asset_kind}",
    responses={
        status.HTTP_200_OK: {"description": "Image uploaded and resized"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid asset kind or upload"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
    },
)
async def upload_game_asset(
    game_id: UUID,
    asset_kind: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if asset_kind not in ALLOWED_ASSET_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported asset kind '{asset_kind}'. Supported values: {sorted(ALLOWED_ASSET_KINDS)}",
        )

    await _get_game_or_404(game_id, db)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is required.",
        )

    image_bytes = await file.read()
    target_path = await save_game_asset(image_bytes, game_id, asset_kind)

    return {
        "game_id": str(game_id),
        "asset_kind": asset_kind,
        "path": str(target_path),
        "status": "saved",
    }


@router.put(
    "/{game_id}/notes/{note_name}",
    responses={
        status.HTTP_201_CREATED: {"description": "Note created or updated"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid note name"},
    },
)
async def set_game_note(
    game_id: UUID,
    note_name: str,
    payload: NoteWrite = Body(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | None]:
    game = await _get_game_or_404(game_id, db)
    note_path = _game_note_path(game, note_name)
    # This write operation is inherently local (file system), so it doesn't require the DB transaction context.
    note_path.write_text(payload.content, encoding="utf-8")

    return {
        "game_id": str(game_id),
        "note_name": _normalize_note_name(note_name),
        "path": str(note_path),
        "status": "saved",
    }


@router.get(
    "/{game_id}/notes",
    responses={
        status.HTTP_200_OK: {"description": "List of markdown notes for the game"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
    },
)
async def list_game_notes(
    game_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[str]]:
    # Read operations do not need transaction wrappers for read consistency
    game = await _get_game_or_404(game_id, db)

    if not game.folder_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game folder_location is missing.",
        )
    
    notes_dir = _DATA_ROOT / game.folder_location / "notes"
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
    db: AsyncSession = Depends(get_db),
) -> Response:
    # Read operation
    game = await _get_game_or_404(game_id, db)
    note_path = _game_note_path(game, note_name)

    if not note_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note '{_normalize_note_name(note_name)}' not found for game {game_id}",
        )

    return Response(content=note_path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


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
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    game = await _get_game_or_404(game_id, db)
    # File operation (local filesystem), does not require DB transaction scope.
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


@router.post(
    "/create",
    response_model=GameRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Duplicate folder_location",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "duplicate_folder_location",
                            "field": "folder_location",
                            "value": "ExistingFolder",
                            "message": "A game with folder_location 'ExistingFolder' already exists.",
                        }
                    }
                }
            },
        }
    },
)
async def create_game(payload: GameCreate, db: AsyncSession = Depends(get_db)) -> Game:
    # Use the transaction scope to ensure atomicity for all DB writes.
    async with run_transaction(get_db):
        await _ensure_folder_location_available(payload.folder_location, db)

        data = payload.model_dump()
        if not data.get("sort_title"):
            # Note: This call to _derive_sort_title is pure Python and doesn't need the DB session 'db'
            data["sort_title"] = _derive_sort_title(data["title"])

        game = Game(**data)
        db.add(game)
        
        # The run_transaction context manager handles commit/rollback automatically here.
        await db.flush() # Flush to ensure the object ID is generated and used below
        await db.refresh(game)
        return game


@router.get("/list", response_model=list[GameRead])
async def list_games(
    db: AsyncSession = Depends(get_db),
    status_filter: GameStatus | None = Query(default=None, alias="status"),
    favorite: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="Case-insensitive title search"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Game]:
    # Read operation - no transaction wrapper needed for simple selects
    stmt = select(Game)

    if status_filter is not None:
        stmt = stmt.where(Game.status == status_filter)
    if favorite is not None:
        stmt = stmt.where(Game.favorite == favorite)
    if search:
        stmt = stmt.where(Game.title.ilike(f"%{search}%"))

    stmt = stmt.order_by(Game.sort_title).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/get/{game_id}", response_model=GameRead)
async def get_game(game_id: UUID, db: AsyncSession = Depends(get_db)) -> Game:
    # Read operation - no transaction wrapper needed for simple selects
    return await _get_game_or_404(game_id, db)


@router.patch(
    "/update/{game_id}",
    response_model=GameRead,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Duplicate folder_location",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "duplicate_folder_location",
                            "field": "folder_location",
                            "value": "ExistingFolder",
                            "message": "A game with folder_location 'ExistingFolder' already exists.",
                        }
                    }
                }
            },
        }
    },
)
async def update_game(
    game_id: UUID, payload: GameUpdate, db: AsyncSession = Depends(get_db)
) -> Game:
    # Use the transaction scope for atomic updates
    async with run_transaction(get_db):
        game = await _get_game_or_404(game_id, db)

        updates = payload.model_dump(exclude_unset=True)

        if "folder_location" in updates and updates["folder_location"] is not None:
            # This check needs the session context, which run_transaction provides
            await _ensure_folder_location_available(
                updates["folder_location"], db, exclude_game_id=game_id
            )

        for field, value in updates.items():
            setattr(game, field, value)

        # Keep sort_title in sync if title changed but sort_title wasn't explicitly set
        if "title" in updates and "sort_title" not in updates:
            game.sort_title = _derive_sort_title(game.title)

        # The run_transaction context manager handles commit/rollback automatically here.
        await db.flush()
        await db.refresh(game)
        return game


@router.delete("/delete/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(game_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    # Use the transaction scope for atomic deletion
    async with run_transaction(get_db):
        game = await _get_game_or_404(game_id, db)
        await db.delete(game)
        # The context manager will handle commit/rollback automatically here.