"""Load the current user's portable library snapshot at the application boundary."""

import time
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.library_export import LibraryExport
from src.database.models.anime import Anime
from src.database.models.game import Game
from src.database.models.movies import Movie
from src.database.models.tv_show import TVShow


async def build_library_export(db: AsyncSession, user_id: UUID) -> LibraryExport:
    groups: dict[str, Any] = {}
    for name, model in (("games", Game), ("movies", Movie), ("tv_shows", TVShow), ("anime", Anime)):
        groups[name] = list(
            (
                await db.execute(
                    select(model)
                    .where(model.user_id == user_id, model.deleted_at.is_(None))
                    .order_by(model.sort_title)
                )
            )
            .scalars()
            .all()
        )
    return LibraryExport(exported_at=int(time.time()), game_count=len(groups["games"]), **groups)
