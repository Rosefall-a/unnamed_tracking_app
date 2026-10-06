"""Re-read the genres of a user's Steam games from the tags players vote on."""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.games import steam, steam_tags

router = APIRouter(
    prefix="/api/library-sync/steam-tags",
    tags=["library-sync"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/refresh")
async def refresh_steam_tags(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=25),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update the tags of Steam games a few at a time, so one request stays
    short. Ask again with the offset you are given until `done` is true. Only
    the tags change; a game whose store page can't be read is left as it is."""
    games = (
        await db.scalars(
            select(Game)
            .where(
                Game.user_id == current_user.id,
                Game.deleted_at.is_(None),
                Game.source == "Steam",
                Game.external_id.is_not(None),
            )
            .order_by(Game.title)
        )
    ).all()
    batch = games[offset : offset + limit]
    updated = 0
    for game in batch:
        try:
            app_id = int(game.external_id or "")
        except ValueError:
            continue
        player_tags = await asyncio.to_thread(steam_tags.fetch_player_tags, app_id)
        if not player_tags:
            continue
        try:
            details = await asyncio.to_thread(steam.get_app_details, app_id)
        # Official genres are optional enrichment; player tags still apply if this lookup fails.
        except Exception:  # pylint: disable=broad-exception-caught
            details = None
        picked = steam_tags.pick_genre_tags(player_tags, steam_tags.official_genre_names(details))
        have = {tag.lower() for tag in picked}
        # whatever else the game was tagged with (your own tags, the source) stays
        new_tags = [*picked, *(tag for tag in game.tags if tag.lower() not in have)]
        if new_tags != game.tags:
            game.tags = new_tags
            updated += 1
    await db.commit()
    return {
        "total": len(games),
        "offset": offset,
        "processed": len(batch),
        "updated": updated,
        "done": offset + len(batch) >= len(games),
    }
