"""What is in a game, counted, so a tab set to "show when it has content" knows
whether to appear. Cheap on purpose: counts only, no file contents."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

from src.api.routes.games import _DATA_ROOT, _get_game_or_404
from src.core.auth import get_current_user
from src.database.models.achievement import Achievement
from src.database.models.game_archive import GameArchive
from src.database.models.game_file_item import GameFileItem
from src.database.models.media_item import MediaItem
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/game", tags=["game page"])


@router.get("/{game_id}/content-counts")
async def content_counts(
    game_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    game = await _get_game_or_404(game_id, db, current_user.id)

    async def count(model: Any, *where: ColumnElement[bool]) -> int:
        return int(await db.scalar(select(sql_count()).select_from(model).where(*where)) or 0)

    media = {
        kind: await count(
            MediaItem,
            MediaItem.game_id == game_id,
            MediaItem.kind == kind,
            MediaItem.deleted_at.is_(None),
        )
        for kind in ("screenshot", "clip", "soundtrack")
    }
    notes = 0
    if game.folder_location:
        directory = _DATA_ROOT / str(game.user_id) / "games" / game.folder_location / "notes"
        if directory.exists():
            notes = sum(1 for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".md")
    return {
        "achievements": await count(Achievement, Achievement.game_id == game_id),
        "screenshots": media["screenshot"],
        "clips": media["clip"],
        "soundtrack": media["soundtrack"],
        "saves": await count(
            GameArchive,
            GameArchive.game_id == game_id,
            GameArchive.kind == "save",
            GameArchive.deleted_at.is_(None),
        ),
        "worlds": await count(
            GameArchive,
            GameArchive.game_id == game_id,
            GameArchive.kind == "world_save",
            GameArchive.deleted_at.is_(None),
        ),
        "docs": await count(
            GameFileItem,
            GameFileItem.game_id == game_id,
            GameFileItem.kind == "doc",
            GameFileItem.deleted_at.is_(None),
        ),
        "notes": notes,
    }
