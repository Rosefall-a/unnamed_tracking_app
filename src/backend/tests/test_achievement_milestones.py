"""Milestones come from the real unlock times: the 100th unlock is the 100th by
time, a perfect game is reached when its last achievement unlocks, and a moment
that cannot be known is left without a date instead of guessed."""

import time
import uuid
from types import SimpleNamespace

from fastapi import Response
from sqlalchemy import delete, func, select

from src.api.routes import games
from src.api.schemas.game import GameCreate
from src.database.models.achievement import Achievement
from src.database.models.notification import Notification
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features import achievement_milestones as ms
from src.features.notifications import generate_for_user


def _row(game, title, name, unlocked, at=None, percent=None):
    return SimpleNamespace(
        game_id=game,
        title=title,
        name=name,
        unlocked=unlocked,
        unlocked_at=at,
        global_percent=percent,
    )


def test_counts_order_and_perfect_games_follow_unlock_times() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    rows = [
        _row(a, "Alpha", "A1", True, 300, 50.0),
        _row(a, "Alpha", "A2", True, 100, 0.8),
        _row(b, "Beta", "B1", True, 200, 7.0),
        _row(b, "Beta", "B2", False),
    ]
    result = ms.build(rows)
    by_id = {m["id"]: m for m in result["reached"]}

    assert by_id["unlocks:1"]["at"] == 100
    assert by_id["unlocks:1"]["achievement"] == "A2"
    # Alpha is perfect when its last one, A1, unlocks; Beta is not perfect
    assert by_id["perfect:1"]["at"] == 300
    assert by_id["perfect:1"]["game_title"] == "Alpha"
    assert "perfect:5" not in by_id
    # B1 (7%) and A2 (0.8%) are both under 10%; A2 came first
    # A2 (0.8%) came first under 10%, 5% and 1%, so it counts once, for 1%
    assert by_id["rarity:1"]["achievement"] == "A2 (0.8%)"
    assert "rarity:10" not in by_id and "rarity:5" not in by_id
    assert "rarity:0.5" not in by_id
    assert result["totals"] == {"unlocked": 3, "perfect": 1}
    assert {n["kind"]: (n["current"], n["target"]) for n in result["next"]} == {
        "unlocks": (3, 100),
        "perfect": (1, 5),
    }
    # newest first
    assert [m["at"] for m in result["reached"]] == sorted(
        [m["at"] for m in result["reached"]], reverse=True
    )


def test_an_unlock_with_no_time_means_no_date_not_a_guess() -> None:
    g = uuid.uuid4()
    result = ms.build([_row(g, "Gamma", "G1", True, None), _row(g, "Gamma", "G2", True, 50)])
    by_id = {m["id"]: m for m in result["reached"]}
    assert by_id["unlocks:1"]["at"] is None
    assert by_id["perfect:1"]["at"] is None
    assert result["reached"][-1]["at"] is None


def test_ordinals_read_naturally() -> None:
    assert [ms._ordinal(n) for n in (1, 2, 3, 11, 12, 13, 21, 100, 1000)] == [
        "1st",
        "2nd",
        "3rd",
        "11th",
        "12th",
        "13th",
        "21st",
        "100th",
        "1,000th",
    ]


async def test_a_new_milestone_is_notified_once_and_old_ones_never() -> None:
    now = int(time.time())
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        user_id = user.id
    try:
        async with SessionLocal() as db:
            game = await games.create_game(
                GameCreate(title="Milestone Test", folder_location="Milestone_Test"),
                Response(),
                db,
                SimpleNamespace(id=user_id),
            )
            # an old unlock (long before the window) and one from an hour ago
            for name, at in (("Old", now - 90 * 86400), ("New", now - 3600)):
                db.add(
                    Achievement(
                        game_id=game.id,
                        provider="Steam",
                        external_id=name,
                        name=name,
                        unlocked=True,
                        unlocked_at=at,
                        created_at=1,
                    )
                )
            await db.commit()
        for _ in range(2):
            async with SessionLocal() as db:
                await generate_for_user(db, user_id)
        async with SessionLocal() as db:
            titles = (
                await db.execute(
                    select(Notification.title).where(
                        Notification.user_id == user_id, Notification.kind == "milestone"
                    )
                )
            ).scalars().all()
            assert titles == ["Your first perfect game"]
            assert (
                await db.scalar(
                    select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
                )
            ) == 1
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
