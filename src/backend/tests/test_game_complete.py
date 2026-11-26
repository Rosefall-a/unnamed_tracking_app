"""A game you have every achievement for: one notice when its last one comes
in, never for a game finished long ago, a game with nothing to unlock or one
marked Mastered by hand with some still locked; and the library summary names
each game's rarest unlock."""

import time
import uuid
from types import SimpleNamespace

from fastapi import Response
from sqlalchemy import delete, select

from src.api.routes import games
from src.api.schemas.game import GameCreate
from src.core.preferences import save_preferences
from src.database.models.achievement import Achievement
from src.database.models.notification import Notification
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features.notifications import _percent, generate_for_user


async def _user() -> uuid.UUID:
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        return user.id


async def _game(db, user_id, title: str, sets: list[tuple[bool, int | None, float | None]]):
    game = await games.create_game(
        GameCreate(title=title, folder_location=title.replace(" ", "_")),
        Response(),
        db,
        SimpleNamespace(id=user_id),
    )
    for i, (unlocked, at, percent) in enumerate(sets):
        db.add(
            Achievement(
                game_id=game.id,
                provider="Steam",
                external_id=f"a{i}",
                name=f"{title} {i}",
                unlocked=unlocked,
                unlocked_at=at,
                global_percent=percent,
                created_at=1,
            )
        )
    await db.commit()
    return game.id


async def _cleanup(user_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def test_only_a_game_finished_just_now_is_announced_once() -> None:
    now = int(time.time())
    user_id = await _user()
    try:
        async with SessionLocal() as db:
            fresh = await _game(
                db, user_id, "Fresh", [(True, now - 7200, 40.0), (True, now - 3600, 5.66)]
            )
            await _game(db, user_id, "Long Ago", [(True, now - 90 * 86400, 3.0)])
            await _game(db, user_id, "Not Yet", [(True, now - 60, 3.0), (False, None, 1.0)])
        for _ in range(2):
            async with SessionLocal() as db:
                await generate_for_user(db, user_id)
        async with SessionLocal() as db:
            rows = (
                (
                    await db.execute(
                        select(Notification).where(
                            Notification.user_id == user_id, Notification.kind == "game_complete"
                        )
                    )
                )
                .scalars()
                .all()
            )
        assert [(n.media_id, n.title, n.event_at) for n in rows] == [(fresh, "Fresh", now - 3600)]
        # exact figures only: the count and the rarest one actually unlocked
        assert rows[0].body == "All 2 achievements · rarest 5.7% of players"
        assert rows[0].poster_url == f"/api/game/{fresh}/assets/key_art"
    finally:
        await _cleanup(user_id)


async def test_switched_off_means_no_notice() -> None:
    now = int(time.time())
    user_id = await _user()
    try:
        async with SessionLocal() as db:
            await save_preferences(db, user_id, {"notify_game_complete": False})
            await _game(db, user_id, "Quiet", [(True, now - 60, None)])
        async with SessionLocal() as db:
            await generate_for_user(db, user_id)
        async with SessionLocal() as db:
            kinds = (
                (await db.execute(select(Notification.kind).where(Notification.user_id == user_id)))
                .scalars()
                .all()
            )
        assert "game_complete" not in kinds
    finally:
        await _cleanup(user_id)


async def test_summary_carries_each_games_rarest_unlock() -> None:
    user_id = await _user()
    try:
        async with SessionLocal() as db:
            a = await _game(
                db, user_id, "Rare", [(True, 1, 30.0), (True, 2, 2.5), (False, None, 0.1)]
            )
            b = await _game(db, user_id, "No Rarity", [(True, 1, None)])
            summary = await games.get_achievements_summary(db, SimpleNamespace(id=user_id))
        # the locked 0.1% one is not yours, so 2.5% is the rarest unlock
        assert summary[str(a)]["total"] == 3
        assert summary[str(a)]["unlocked"] == 2
        assert summary[str(a)]["rarest"]["name"] == "Rare 1"
        assert summary[str(a)]["rarest"]["percent"] == 2.5
        assert "rarest" not in summary[str(b)]
    finally:
        await _cleanup(user_id)


def test_percent_reads_like_the_lists() -> None:
    assert [_percent(v) for v in (1.4, 5.66, 0.05, 10, 12.44, 2.0)] == [
        "1.4%",
        "5.7%",
        "<0.1%",
        "10.0%",
        "12.4%",
        "2.0%",
    ]


async def test_cover_marks_take_any_mix_of_known_marks_only() -> None:
    import pytest

    user_id = await _user()
    try:
        async with SessionLocal() as db:
            saved = await save_preferences(
                db, user_id, {"completion_marks": ["seal", "caption", "seal"]}
            )
            # kept in the app's own order, once each
            assert saved["completion_marks"] == ["caption", "seal"]
            with pytest.raises(ValueError):
                await save_preferences(db, user_id, {"completion_marks": ["ticket"]})
    finally:
        await _cleanup(user_id)


async def test_add_status_takes_only_a_real_status_for_each_library() -> None:
    import pytest

    user_id = await _user()
    try:
        async with SessionLocal() as db:
            saved = await save_preferences(
                db, user_id, {"add_status_game": "wishlist", "add_status_movie": "completed"}
            )
            assert saved["add_status_game"] == "wishlist"
            assert saved["add_status_movie"] == "completed"
            assert saved["add_status_tv"] == "plan"
            # a game status is not a film one, and the other way round
            with pytest.raises(ValueError):
                await save_preferences(db, user_id, {"add_status_movie": "wishlist"})
            with pytest.raises(ValueError):
                await save_preferences(db, user_id, {"add_status_game": "plan"})
    finally:
        await _cleanup(user_id)
