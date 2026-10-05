"""Shared helpers for game-specific API subroutes."""

import re
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.game import Game

_DATA_ROOT = Path("/data/users")
_NOTE_NAME_PATTERN = re.compile(r"^[^\\x00-\\x1f\\x7f/\\\\]+$")

def _normalize_note_name(note_name: str) -> str:
    normalized = note_name.strip()
    if normalized.lower().endswith(".md"):
        normalized = normalized[:-3]

    if (
        not normalized
        or normalized in {".", ".."}
        or normalized.startswith(".")
        or normalized.endswith(".")
        or normalized.endswith(" ")
        or ":" in normalized
        or not _NOTE_NAME_PATTERN.fullmatch(normalized)
        or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])", normalized)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_note_name",
                "message": (
                    "Note title must be a normal file name: spaces and common punctuation are allowed, "
                    "but path separators, control characters, absolute paths, drive-style names, "
                    "and path-like titles are not allowed."
                ),
            },
        )
    return normalized


def _game_note_path(game: Game, note_name: str) -> Path:
    if not game.folder_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game folder_location is missing.",
        )

    note_file_name = f"{_normalize_note_name(note_name)}.md"
    note_dir = _DATA_ROOT / str(game.user_id) / "games" / game.folder_location / "notes"
    note_dir.mkdir(parents=True, exist_ok=True)
    return note_dir / note_file_name


async def _get_game_or_404(
    game_id: UUID, db: AsyncSession, user_id: UUID, include_deleted: bool = False
) -> Game:
    stmt = select(Game).where(Game.id == game_id, Game.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(Game.deleted_at.is_(None))
    game = await db.scalar(stmt)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )
    return game

