"""A game in the trash is not part of the library, so the stats do not count it."""

import time

from src.database.models.game import Game, GameStatus
from src.database.session import SessionLocal
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def test_trashed_games_are_not_counted(flow) -> None:
    before = (await flow.client.get("/api/stats/overview")).json()
    async with SessionLocal() as db:
        db.add(
            Game(
                user_id=flow.user_id,
                title="In the trash",
                sort_title="in the trash",
                folder_location="In-the-trash",
                status=GameStatus.BACKLOG,
                playtime_seconds=7200,
                deleted_at=int(time.time()),
            )
        )
        await db.commit()
    after = (await flow.client.get("/api/stats/overview")).json()
    assert after == before
