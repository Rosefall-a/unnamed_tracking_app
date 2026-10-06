"""The parts of a game's notes beyond writing them: pin, tags and the
achievement a note is about, duplicating and moving a note, earlier versions,
and searching notes across every game. Creating, editing, renaming and
deleting a note are in games.py next to the other note routes."""

import shutil
import time
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.games import (
    _DATA_ROOT,
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
