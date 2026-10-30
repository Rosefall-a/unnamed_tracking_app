"""Steam games an import saved but never filled in."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.game import Game
from src.helpers.save_game_asset import ASSET_FILENAMES, DATA_ROOT


async def bare_steam_game_ids(db: AsyncSession, user_id: UUID) -> list[str]:
    """Steam games an earlier import saved but never finished filling in (the
    page was closed, or Steam turned the request away), so the next import can
    try them again. Only games nobody has touched: no description, developer
    or locked field and no cover, so a re-run can never overwrite an edit."""
    rows = await db.scalars(
        select(Game).where(
            Game.user_id == user_id,
            Game.source == "Steam",
            Game.deleted_at.is_(None),
            Game.external_id.is_not(None),
            Game.description.is_(None),
            Game.developer.is_(None),
        )
    )
    bare = []
    for game in rows.all():
        if game.locked_fields:
            continue
        folder = DATA_ROOT / str(user_id) / "games" / (game.folder_location or "")
        if game.folder_location and (folder / ASSET_FILENAMES["key_art"]).is_file():
            continue
        bare.append(str(game.id))
    return bare
