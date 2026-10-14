"""Emptying the media trash, and the optional automatic clear-out."""

import time

from sqlalchemy import select

from src.core import preferences
from src.database.models.movies import Movie
from src.database.session import SessionLocal
from src.features.trash.sweep import purge_expired_media_trash
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def _movie(user_id, title, deleted_at):
    async with SessionLocal() as db:
        movie = Movie(user_id=user_id, title=title, sort_title=title.lower(), deleted_at=deleted_at)
        db.add(movie)
        await db.commit()
        return movie.id


async def _titles(user_id):
    async with SessionLocal() as db:
        rows = await db.execute(select(Movie.title).where(Movie.user_id == user_id))
        return sorted(rows.scalars().all())


async def test_emptying_the_trash_removes_only_what_is_in_it(flow) -> None:  # noqa: F811
    now = int(time.time())
    await _movie(flow.user_id, "Kept", None)
    await _movie(flow.user_id, "Deleted one", now)
    await _movie(flow.user_id, "Deleted two", now)

    response = await flow.client.post("/api/movie/trash/empty")
    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    assert await _titles(flow.user_id) == ["Kept"]


async def test_nothing_is_cleared_automatically_unless_a_period_is_chosen(flow) -> None:  # noqa: F811
    now = int(time.time())
    await _movie(flow.user_id, "Old", now - 40 * 86400)
    assert preferences.DEFAULTS["media_trash_retention_days"] == 0
    await purge_expired_media_trash()
    assert await _titles(flow.user_id) == ["Old"]


async def test_a_chosen_period_clears_only_older_titles(flow) -> None:  # noqa: F811
    now = int(time.time())
    await _movie(flow.user_id, "Old", now - 40 * 86400)
    await _movie(flow.user_id, "Recent", now - 2 * 86400)
    await _movie(flow.user_id, "Kept", None)
    async with SessionLocal() as db:
        await preferences.save_preferences(db, flow.user_id, {"media_trash_retention_days": 30})
    await purge_expired_media_trash()
    assert await _titles(flow.user_id) == ["Kept", "Recent"]
