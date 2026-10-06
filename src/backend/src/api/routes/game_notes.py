"""The parts of a game's notes beyond writing them: pin, tags and the
achievement a note is about, duplicating and moving a note, earlier versions,
and searching notes across every game. Basic note CRUD shares this module."""

import os
import shutil
import time
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.utils.games import (
    _DATA_ROOT,
    _game_note_path,
    _get_game_or_404,
    _normalize_note_name,
    _note_summary,
)
from src.core.auth import get_current_user
from src.database.models.achievement import Achievement
from src.database.models.game import Game
from src.database.models.game_note_detail import GameNoteDetail, GameNoteVersion
from src.database.models.user import User
from src.database.session import get_db
from src.features import game_notes

_DB_DEPENDENCY = Depends(get_db)


_CURRENT_USER_DEPENDENCY = Depends(get_current_user)


_BODY_DOTDOTDOT = Body(...)


router = APIRouter(prefix="/api/game", tags=["game notes"])

_DB = Depends(get_db)
_USER = Depends(get_current_user)


def _notes_dir(game: Game) -> Path:
    if not game.folder_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Game folder_location is missing."
        )
    return _DATA_ROOT / str(game.user_id) / "games" / game.folder_location / "notes"


def _existing_note(game: Game, note_name: str) -> tuple[str, Path]:
    name = _normalize_note_name(note_name)
    path = _notes_dir(game) / f"{name}.md"
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f'Note "{name}" was not found.'
        )
    return name, path


def _free_name(directory: Path, wanted: str) -> str:
    """`wanted`, or `wanted 2`, `wanted 3`... when that note already exists."""
    if not (directory / f"{wanted}.md").exists():
        return wanted
    n = 2
    while (directory / f"{wanted} {n}.md").exists():
        n += 1
    return f"{wanted} {n}"


# ---------------------------------------------------------------- search ----


# Keep the established workflow and public parameters together.
# pylint: disable=too-many-locals
@router.get("/notes/search")
async def search_notes(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = _DB,
    current_user: User = _USER,
) -> dict[str, list[dict]]:
    """Notes from every game whose name or text contains the query."""
    needle = q.strip().lower()
    games = (
        await db.scalars(
            select(Game).where(Game.user_id == current_user.id, Game.deleted_at.is_(None))
        )
    ).all()
    pinned = {
        (r.game_id, r.name)
        for r in (
            await db.scalars(
                select(GameNoteDetail).where(
                    GameNoteDetail.game_id.in_([g.id for g in games]),
                    GameNoteDetail.pinned.is_(True),
                )
            )
        ).all()
    }
    hits: list[tuple[int, int, dict]] = []
    for game in games:
        if not game.folder_location:
            continue
        directory = _notes_dir(game)
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if not path.is_file() or path.suffix.lower() != ".md":
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            in_name = needle in path.stem.lower()
            at = text.lower().find(needle)
            if not in_name and at == -1:
                continue
            snippet = ""
            if at != -1:
                start = max(0, at - 60)
                snippet = (("…" if start else "") + text[start : at + len(needle) + 90]).replace(
                    "\n", " "
                )
            hits.append(
                (
                    0 if in_name else 1,
                    -int(path.stat().st_mtime),
                    {
                        "game_id": str(game.id),
                        "game_title": game.title,
                        "name": path.stem,
                        "snippet": snippet or text[:150].replace("\n", " "),
                        "updated_at": int(path.stat().st_mtime),
                        "pinned": (game.id, path.stem) in pinned,
                    },
                )
            )
    hits.sort(key=lambda h: (h[0], h[1]))
    return {"notes": [h[2] for h in hits[:limit]]}


# pylint: enable=too-many-locals


# --------------------------------------------------------------- details ----


class NoteDetailsUpdate(BaseModel):
    pinned: bool | None = None
    tags: list[str] | None = Field(default=None, max_length=50)
    linked_achievement_id: UUID | None = None


@router.patch("/{game_id}/notes/{note_name}/details")
async def update_note_details(
    game_id: UUID,
    note_name: str,
    payload: NoteDetailsUpdate,
    db: AsyncSession = _DB,
    current_user: User = _USER,
) -> dict:
    game = await _get_game_or_404(game_id, db, current_user.id)
    name, path = _existing_note(game, note_name)
    row = await game_notes.ensure_row(db, game_id, name, created_at=int(path.stat().st_mtime))
    changes = payload.model_dump(exclude_unset=True)
    if "pinned" in changes and changes["pinned"] is not None:
        row.pinned = changes["pinned"]
    if "tags" in changes and changes["tags"] is not None:
        row.tags = game_notes.clean_tags(changes["tags"])
    if "linked_achievement_id" in changes:
        wanted = changes["linked_achievement_id"]
        if wanted is not None:
            owns = await db.scalar(
                select(Achievement.id).where(
                    Achievement.id == wanted, Achievement.game_id == game_id
                )
            )
            if owns is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="That achievement is not on this game.",
                )
        row.linked_achievement_id = wanted
    await db.commit()
    return _note_summary(path, row)


# ------------------------------------------------- duplicate and move ----


@router.post("/{game_id}/notes/{note_name}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_note(
    game_id: UUID,
    note_name: str,
    db: AsyncSession = _DB,
    current_user: User = _USER,
) -> dict:
    game = await _get_game_or_404(game_id, db, current_user.id)
    name, path = _existing_note(game, note_name)
    directory = path.parent
    copy_name = _free_name(directory, f"{name} copy")
    target = directory / f"{copy_name}.md"
    shutil.copyfile(path, target)
    source = await game_notes.ensure_row(db, game_id, name, created_at=int(path.stat().st_mtime))
    row = await game_notes.ensure_row(db, game_id, copy_name)
    row.tags = list(source.tags)
    row.linked_achievement_id = source.linked_achievement_id
    await db.commit()
    return _note_summary(target, row)


class NoteMove(BaseModel):
    target_game_id: UUID


@router.post("/{game_id}/notes/{note_name}/move")
async def move_note(
    game_id: UUID,
    note_name: str,
    payload: NoteMove,
    db: AsyncSession = _DB,
    current_user: User = _USER,
) -> dict:
    """Move a note, with its tags, pin and saved versions, to another game. The
    achievement it was tied to is dropped, since it belongs to the old game."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    target_game = await _get_game_or_404(payload.target_game_id, db, current_user.id)
    if target_game.id == game.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The note is already in that game."
        )
    name, path = _existing_note(game, note_name)
    target_dir = _notes_dir(target_game)
    target_dir.mkdir(parents=True, exist_ok=True)
    new_name = _free_name(target_dir, name)
    destination = target_dir / f"{new_name}.md"
    row = await game_notes.ensure_row(db, game_id, name, created_at=int(path.stat().st_mtime))
    shutil.move(str(path), str(destination))
    row.game_id = target_game.id
    row.name = new_name
    row.linked_achievement_id = None
    await db.commit()
    return {
        "game_id": str(target_game.id),
        "game_title": target_game.title,
        "note": _note_summary(destination, row),
    }


# -------------------------------------------------------------- versions ----


@router.get("/{game_id}/notes/{note_name}/versions")
async def list_note_versions(
    game_id: UUID,
    note_name: str,
    db: AsyncSession = _DB,
    current_user: User = _USER,
) -> dict[str, list[dict]]:
    game = await _get_game_or_404(game_id, db, current_user.id)
    name, path = _existing_note(game, note_name)
    row = await game_notes.ensure_row(db, game_id, name, created_at=int(path.stat().st_mtime))
    versions = (
        await db.scalars(
            select(GameNoteVersion)
            .where(GameNoteVersion.note_id == row.id)
            .order_by(GameNoteVersion.saved_at.desc(), GameNoteVersion.id)
        )
    ).all()
    await db.commit()
    return {
        "versions": [
            {
                "id": str(v.id),
                "saved_at": v.saved_at // 1000,
                "words": len(v.content.split()),
                "preview": v.content[:200],
            }
            for v in versions
        ]
    }


async def _version_or_404(
    db: AsyncSession, game_id: UUID, name: str, version_id: UUID
) -> tuple[GameNoteDetail, GameNoteVersion]:
    row = await db.scalar(
        select(GameNoteDetail).where(GameNoteDetail.game_id == game_id, GameNoteDetail.name == name)
    )
    version = (
        await db.scalar(
            select(GameNoteVersion).where(
                GameNoteVersion.id == version_id, GameNoteVersion.note_id == row.id
            )
        )
        if row
        else None
    )
    if row is None or version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")
    return row, version


@router.get("/{game_id}/notes/{note_name}/versions/{version_id}")
async def get_note_version(
    game_id: UUID,
    note_name: str,
    version_id: UUID,
    db: AsyncSession = _DB,
    current_user: User = _USER,
) -> dict:
    game = await _get_game_or_404(game_id, db, current_user.id)
    name, _path = _existing_note(game, note_name)
    _row, version = await _version_or_404(db, game_id, name, version_id)
    return {
        "id": str(version.id),
        "saved_at": version.saved_at // 1000,
        "content": version.content,
    }


@router.post("/{game_id}/notes/{note_name}/versions/{version_id}/restore")
async def restore_note_version(
    game_id: UUID,
    note_name: str,
    version_id: UUID,
    db: AsyncSession = _DB,
    current_user: User = _USER,
) -> dict:
    """Put an earlier version back. What is there now is kept as a version first,
    so a restore can be undone."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    name, path = _existing_note(game, note_name)
    row, version = await _version_or_404(db, game_id, name, version_id)
    current = path.read_text(encoding="utf-8", errors="replace")
    restored = version.content
    if current != restored:
        await game_notes.record_version(db, row, current)
        path.write_text(restored, encoding="utf-8")
    await db.commit()
    return {"note_name": name, "restored_from": version.saved_at // 1000, "now": int(time.time())}


crud_router = APIRouter()


class NoteWrite(BaseModel):
    """Request body used to create or update a game note."""

    __module__ = "src.api.routes.games"
    content: str


class NoteRename(BaseModel):
    """Request body used to rename a game note."""

    __module__ = "src.api.routes.games"
    new_name: str


@crud_router.post(
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
            detail={
                "error": "note_already_exists",
                "message": f'A note titled "{normalized_name}" already exists.',
            },
        ) from exc
    await game_notes.ensure_row(db, game_id, normalized_name)
    await db.commit()
    return {
        "game_id": str(game_id),
        "note_name": normalized_name,
        "path": str(note_path),
        "status": "saved",
    }


@crud_router.put(
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f'Note "{normalized_name}" was not found.'
        )
    previous = note_path.read_text(encoding="utf-8", errors="replace")
    row = await game_notes.ensure_row(
        db, game_id, normalized_name, created_at=int(note_path.stat().st_mtime)
    )
    if previous != payload.content:
        await game_notes.record_version(db, row, previous)
    note_path.write_text(payload.content, encoding="utf-8")
    await db.commit()
    return {
        "game_id": str(game_id),
        "note_name": normalized_name,
        "path": str(note_path),
        "status": "saved",
    }


@crud_router.patch(
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f'Note "{source_name}" was not found.'
        )
    if source_name == destination_name:
        return {
            "game_id": str(game_id),
            "note_name": source_name,
            "path": str(source_path),
            "status": "saved",
        }
    try:
        os.link(source_path, destination_path)
    except FileExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "note_already_exists",
                "message": f'A note titled "{destination_name}" already exists.',
            },
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The note could not be renamed.",
        ) from exc
    try:
        source_path.unlink()
    except OSError as exc:
        try:
            destination_path.unlink()
        except OSError:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The note could not be renamed.",
        ) from exc
    await game_notes.rename_row(db, game_id, source_name, destination_name)
    await db.commit()
    return {
        "game_id": str(game_id),
        "note_name": destination_name,
        "path": str(destination_path),
        "status": "saved",
    }


@crud_router.get(
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


@crud_router.get("/{game_id}/notes-summary")
async def list_game_note_summaries(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    """The notes with their edit time, length and a preview, for the Notes tab."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    if not game.folder_location:
        return {"notes": []}
    notes_dir = _DATA_ROOT / str(game.user_id) / "games" / game.folder_location / "notes"
    if not notes_dir.exists():
        return {"notes": []}
    rows = await game_notes.sync_rows(db, game_id, notes_dir)
    paths = [p for p in notes_dir.iterdir() if p.is_file() and p.suffix.lower() == ".md"]
    return {
        "notes": [
            _note_summary(p, rows.get(p.stem)) for p in sorted(paths, key=lambda p: p.stem.lower())
        ]
    }


@crud_router.get(
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


@crud_router.delete(
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
    await game_notes.delete_row(db, game_id, _normalize_note_name(note_name))
    await db.commit()
    return {
        "game_id": str(game_id),
        "note_name": _normalize_note_name(note_name),
        "status": "deleted",
    }
