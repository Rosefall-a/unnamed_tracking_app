"""Owned game details and evidence metadata for public plugin consumers."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.achievement import Achievement
from src.database.models.game import Game
from src.database.models.media_item import MediaItem

_PUBLIC_FIELDS = (
    "id",
    "title",
    "sort_title",
    "description",
    "release_date",
    "developer",
    "publisher",
    "series",
    "tags",
    "features",
    "source",
    "platform",
    "region",
    "language",
    "status",
    "priority",
    "favorite",
    "playtime_seconds",
    "completion_date",
    "last_played_at",
    "created_at",
    "updated_at",
    "rating_story",
    "rating_gameplay",
    "rating_soundtrack",
    "rating_overall",
    "collections",
    "time_to_beat_hours",
)


def game_details(game: Game, *, total: int = 0, unlocked: int = 0) -> dict[str, Any]:
    result = jsonable_encoder({key: getattr(game, key) for key in _PUBLIC_FIELDS})
    result["achievement_total"] = total
    result["achievement_unlocked"] = unlocked
    result["assets"] = {
        kind: f"/api/game/{game.id}/assets/{kind}" for kind in ("key_art", "banner", "logo", "icon")
    }
    return result


async def owned_game(db: AsyncSession, user_id: UUID, value: Any) -> Game:
    game_id = UUID(str(value))
    game = await db.scalar(
        select(Game).where(Game.id == game_id, Game.user_id == user_id, Game.deleted_at.is_(None))
    )
    if game is None:
        raise LookupError("game not found")
    return game


async def dispatch_game_library(
    db: AsyncSession, *, user_id: UUID, method: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Return bounded DTO pages; filesystem paths and credentials stay private."""
    offset = max(0, int(payload.get("offset", 0)))
    limit = max(1, min(int(payload.get("limit", 50)), 200))
    if method == "games.details.list":
        games = list(
            (
                await db.execute(
                    select(Game)
                    .where(Game.user_id == user_id, Game.deleted_at.is_(None))
                    .order_by(Game.sort_title, Game.title, Game.id)
                    .offset(offset)
                    .limit(limit + 1)
                )
            )
            .scalars()
            .all()
        )
        ids = [game.id for game in games[:limit]]
        counts = (
            {
                game_id: (total, unlocked)
                for game_id, total, unlocked in (
                    await db.execute(
                        select(
                            Achievement.game_id,
                            func.count(),
                            func.count().filter(Achievement.unlocked.is_(True)),
                        )
                        .where(Achievement.game_id.in_(ids))
                        .group_by(Achievement.game_id)
                    )
                ).all()
            }
            if ids
            else {}
        )
        return {
            "games": [
                game_details(
                    game,
                    total=counts.get(game.id, (0, 0))[0],
                    unlocked=counts.get(game.id, (0, 0))[1],
                )
                for game in games[:limit]
            ],
            "next_offset": offset + min(len(games), limit),
            "complete": len(games) <= limit,
        }
    game = await owned_game(db, user_id, payload.get("game_id"))
    if method == "games.get":
        achievements = list(
            (
                await db.execute(
                    select(Achievement)
                    .where(Achievement.game_id == game.id)
                    .order_by(Achievement.id)
                    .offset(offset)
                    .limit(limit + 1)
                )
            )
            .scalars()
            .all()
        )
        return {
            "game": game_details(game),
            "achievements": [
                jsonable_encoder(
                    {
                        key: getattr(item, key)
                        for key in (
                            "id",
                            "provider",
                            "external_id",
                            "name",
                            "description",
                            "icon_url",
                            "unlocked",
                            "unlocked_at",
                            "tier",
                        )
                    }
                )
                for item in achievements[:limit]
            ],
            "next_offset": offset + min(len(achievements), limit),
            "complete": len(achievements) <= limit,
        }
    if method == "games.media.list":
        items = list(
            (
                await db.execute(
                    select(MediaItem)
                    .where(MediaItem.game_id == game.id, MediaItem.deleted_at.is_(None))
                    .order_by(MediaItem.created_at, MediaItem.id)
                    .offset(offset)
                    .limit(limit + 1)
                )
            )
            .scalars()
            .all()
        )
        return {
            "media": [
                jsonable_encoder(
                    {
                        "id": item.id,
                        "filename": item.filename,
                        "kind": item.kind,
                        "tags": item.tags,
                        "note": item.note,
                        "linked_achievement_id": item.linked_achievement_id,
                        "profile_id": item.profile_id,
                        "created_at": item.created_at,
                        "url": f"/api/game/{game.id}/screenshots/{item.kind}/{quote(item.filename, safe='')}",
                    }
                )
                for item in items[:limit]
            ],
            "next_offset": offset + min(len(items), limit),
            "complete": len(items) <= limit,
        }
    raise ValueError("unsupported game library method")
