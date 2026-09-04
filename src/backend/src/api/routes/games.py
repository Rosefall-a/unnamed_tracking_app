"""API routes for managing games, notes, and game artwork."""

import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import requests
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.game import GameCreate, GameRead, GameUpdate
from src.database.models.game import Game, GameStatus
from src.database.models.user import User
from src.database.session import get_db
from src.core.auth import get_current_user
from src.features.metadata.games.search import search_game_metadata
from src.helpers.save_game_asset import ASSET_FILENAMES, AssetKind, create_game_folder, save_game_asset

router = APIRouter(
    prefix="/api/game",
    tags=["game"],
    dependencies=[Depends(get_current_user)],
)

_DATA_ROOT = Path("/data/games")
_NOTE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_LEADING_ARTICLE = re.compile(r"^(a|an|the)\s+", flags=re.IGNORECASE)


class NoteWrite(BaseModel):
    """Request body used to create or replace a game note."""

    content: str


class MetadataSearchResponse(BaseModel):
    query: str
    providers: list[str]
    provider_errors: list[str] = []
    results: list[dict]


class AssetUrlRequest(BaseModel):
    url: str


ALLOWED_ASSET_KINDS = {"key_art", "banner", "logo", "icon"}


@router.get("/metadata/search", response_model=MetadataSearchResponse)
async def search_metadata(
    query: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(default=8, ge=1, le=20),
) -> dict:
    """Search external providers for data that can prefill a new game."""
    try:
        return await asyncio.to_thread(search_game_metadata, query.strip(), limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Metadata providers could not be reached: {exc}",
        ) from exc


@router.get("/{game_id}/assets/{asset_kind}", response_class=FileResponse)
async def get_game_asset(
    game_id: UUID,
    asset_kind: AssetKind,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Return a stored PNG asset for a game."""
    if asset_kind not in ALLOWED_ASSET_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported asset kind '{asset_kind}'. Supported values: {sorted(ALLOWED_ASSET_KINDS)}",
        )

    game = await _get_game_or_404(game_id, db, current_user.id)
    asset_path = _DATA_ROOT / game.folder_location / ASSET_FILENAMES[asset_kind]
    if not asset_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_kind}' has not been uploaded for game {game_id}.",
        )

    return FileResponse(
        asset_path,
        media_type="image/png",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


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


async def _get_game_or_404(game_id: UUID, db: AsyncSession, user_id: UUID) -> Game:
    game = await db.scalar(select(Game).where(Game.id == game_id, Game.user_id == user_id))
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
    asset_kind: AssetKind,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Upload and persist artwork for a game."""
    if asset_kind not in ALLOWED_ASSET_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported asset kind '{asset_kind}'. Supported values: {sorted(ALLOWED_ASSET_KINDS)}",
        )

    await _get_game_or_404(game_id, db, current_user.id)

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


@router.post(
    "/{game_id}/assets/{asset_kind}/from-url",
    responses={
        status.HTTP_200_OK: {"description": "Image downloaded and resized"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid URL or image"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
    },
)
async def download_game_asset(
    game_id: UUID,
    asset_kind: AssetKind,
    payload: AssetUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Download an image URL and persist it as a normalized game asset."""
    if asset_kind not in ALLOWED_ASSET_KINDS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported asset kind '{asset_kind}'.")

    await _get_game_or_404(game_id, db, current_user.id)
    parsed_url = urlparse(payload.url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image URL must use http or https.")

    try:
        response = await asyncio.to_thread(requests.get, payload.url, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not download image: {exc}") from exc

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL did not return an image.")
    image_bytes = response.content
    if len(image_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is larger than the 15 MB limit.")

    try:
        output_path = await save_game_asset(image_bytes, game_id, asset_kind)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not save image: {exc}") from exc

    return {
        "game_id": str(game_id),
        "asset_kind": asset_kind,
        "path": str(output_path),
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
    current_user: User = Depends(get_current_user),
) -> dict[str, str | None]:
    """Create or replace a markdown note for a game."""
    game = await _get_game_or_404(game_id, db, current_user.id)
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
    current_user: User = Depends(get_current_user),
) -> dict[str, list[str]]:
    """Return the markdown note names associated with a game."""
    game = await _get_game_or_404(game_id, db, current_user.id)

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
    current_user: User = Depends(get_current_user),
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
async def create_game(
    payload: GameCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Game:
    """Create a game after validating its folder location."""
    await _ensure_folder_location_available(payload.folder_location, db)

    data = payload.model_dump()
    data["user_id"] = current_user.id
    if not data.get("sort_title"):
        data["sort_title"] = _derive_sort_title(data["title"])

    game = Game(**data)
    db.add(game)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _duplicate_folder_error(payload.folder_location) from exc

    await db.refresh(game)
    create_game_folder(game.folder_location)
    return game


@router.get("/list", response_model=list[GameRead])
async def list_games(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: GameStatus | None = Query(default=None, alias="status"),
    favorite: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="Case-insensitive title search"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Game]:
    """Return games filtered by status, favorite flag, or title search."""
    stmt = select(Game).where(Game.user_id == current_user.id)

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
async def get_game(
    game_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Game:
    """Return one game by ID."""
    return await _get_game_or_404(game_id, db, current_user.id)


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
    game_id: UUID,
    payload: GameUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Game:
    """Update a game and keep its derived sort title synchronized."""
    game = await _get_game_or_404(game_id, db, current_user.id)

    updates = payload.model_dump(exclude_unset=True)

    if "folder_location" in updates and updates["folder_location"] is not None:
        await _ensure_folder_location_available(
            updates["folder_location"], db, exclude_game_id=game_id
        )

    for field, value in updates.items():
        setattr(game, field, value)

    # Keep sort_title in sync if title changed but sort_title wasn't explicitly set
    if "title" in updates and "sort_title" not in updates:
        game.sort_title = _derive_sort_title(game.title)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _duplicate_folder_error(game.folder_location) from exc

    await db.refresh(game)
    return game


@router.delete("/delete/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(
    game_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a game by ID."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    await db.delete(game)
    await db.commit()
