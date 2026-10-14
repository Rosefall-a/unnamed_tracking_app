"""A game added by hand and the same game from a Steam sync: pair them up, never merge
on their own, and let the person merge, keep both, or change their mind."""

from datetime import date
from types import SimpleNamespace

from sqlalchemy import select

from src.core.auth import get_current_user
from src.database.models.achievement import Achievement
from src.database.models.game import Game, GameStatus
from src.database.models.notification import Notification
from src.database.session import SessionLocal
from src.features.game_matches import find_matches, match_key
from src.main import app
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def _game(user_id, title, folder, **fields) -> str:
    async with SessionLocal() as db:
        game = Game(
            user_id=user_id,
            title=title,
            sort_title=title.lower(),
            folder_location=folder,
            status=GameStatus.BACKLOG,
            **fields,
        )
        db.add(game)
        await db.commit()
        return str(game.id)


async def _steam(user_id, title, folder, **fields) -> str:
    return await _game(
        user_id, title, folder, source="Steam", external_id="1145360", playtime_seconds=7200, **fields
    )


async def _achievement(game_id: str) -> None:
    async with SessionLocal() as db:
        db.add(
            Achievement(
                game_id=game_id, provider="Steam", external_id="ACH_1", name="First", unlocked=True
            )
        )
        await db.commit()


def _as_user(flow) -> None:  # noqa: F811
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=flow.user_id)


def test_titles_differing_only_in_marks_and_case_are_the_same() -> None:
    assert match_key("Hades™") == match_key("hades")
    assert match_key("Baldur's Gate 3") == match_key("Baldurs Gate 3")
    assert match_key("Hades") != match_key("Hades II")


async def test_a_manual_game_and_a_steam_game_with_one_title_are_paired(flow) -> None:
    mine = await _game(flow.user_id, "Hades", "Hades-mine")
    theirs = await _steam(flow.user_id, "Hades™", "Hades-steam")
    await _game(flow.user_id, "Celeste", "Celeste")  # nothing to pair with

    async with SessionLocal() as db:
        assert await find_matches(db, flow.user_id) == 1
        assert await find_matches(db, flow.user_id) == 0  # asking again finds nothing new
        await db.commit()
        notes = (
            await db.scalars(select(Notification).where(Notification.user_id == flow.user_id))
        ).all()
    assert [n.kind for n in notes] == ["possible_duplicate"]
    assert str(notes[0].media_id) == theirs

    _as_user(flow)
    listed = (await flow.client.get("/api/game-matches")).json()
    assert listed["pending"] == 1
    assert listed["items"][0]["original"]["id"] == mine


async def test_a_remake_with_the_same_name_is_not_paired(flow) -> None:
    await _game(flow.user_id, "Prey", "Prey-2006", release_date=date(2006, 7, 11))
    await _steam(flow.user_id, "Prey", "Prey-2017", release_date=date(2017, 5, 5))
    async with SessionLocal() as db:
        assert await find_matches(db, flow.user_id) == 0


async def test_merging_keeps_my_game_and_takes_the_steam_identity(flow) -> None:
    mine = await _game(
        flow.user_id, "Hades", "Hades-mine", description="my words", locked_fields=["description"]
    )
    theirs = await _steam(flow.user_id, "Hades", "Hades-steam", developer="Supergiant")
    await _achievement(theirs)
    async with SessionLocal() as db:
        await find_matches(db, flow.user_id)
        await db.commit()
    _as_user(flow)
    match_id = (await flow.client.get("/api/game-matches")).json()["items"][0]["id"]

    done = await flow.client.post(f"/api/game-matches/{match_id}/merge", json={"prefer": "steam"})
    assert done.status_code == 200 and done.json()["status"] == "merged"

    async with SessionLocal() as db:
        kept = await db.get(Game, mine)
        gone = await db.get(Game, theirs)
        assert (kept.source, kept.external_id) == ("Steam", "1145360")
        assert kept.playtime_seconds == 7200
        assert kept.developer == "Supergiant"  # it had none
        assert kept.description == "my words"  # locked, so Steam's never replaces it
        assert gone.deleted_at is not None
        moved = (await db.scalars(select(Achievement).where(Achievement.game_id == kept.id))).all()
        assert len(moved) == 1


async def test_a_merge_can_be_undone(flow) -> None:
    mine = await _game(flow.user_id, "Hades", "Hades-mine", platform="PC")
    theirs = await _steam(flow.user_id, "Hades", "Hades-steam", developer="Supergiant")
    await _achievement(theirs)
    async with SessionLocal() as db:
        await find_matches(db, flow.user_id)
        await db.commit()
    _as_user(flow)
    match_id = (await flow.client.get("/api/game-matches")).json()["items"][0]["id"]
    await flow.client.post(f"/api/game-matches/{match_id}/merge", json={"prefer": "mine"})

    back = await flow.client.post(f"/api/game-matches/{match_id}/reopen")
    assert back.json()["status"] == "pending"

    async with SessionLocal() as db:
        original = await db.get(Game, mine)
        restored = await db.get(Game, theirs)
        assert original.source is None and original.external_id is None
        assert original.developer is None
        assert restored.deleted_at is None
        owned = (await db.scalars(select(Achievement).where(Achievement.game_id == restored.id))).all()
        assert len(owned) == 1


async def test_keeping_both_is_remembered_and_can_be_changed(flow) -> None:
    await _game(flow.user_id, "Hades", "Hades-mine")
    await _steam(flow.user_id, "Hades", "Hades-steam")
    async with SessionLocal() as db:
        await find_matches(db, flow.user_id)
        await db.commit()
    _as_user(flow)
    match_id = (await flow.client.get("/api/game-matches")).json()["items"][0]["id"]

    kept = await flow.client.post(f"/api/game-matches/{match_id}/keep-both")
    assert kept.json()["status"] == "kept_both"
    async with SessionLocal() as db:
        assert await find_matches(db, flow.user_id) == 0  # not asked about again
    assert (await flow.client.get("/api/game-matches")).json()["pending"] == 0

    again = await flow.client.post(f"/api/game-matches/{match_id}/reopen")
    assert again.json()["status"] == "pending"

    merged = await flow.client.post(f"/api/game-matches/{match_id}/merge", json={})
    assert merged.status_code == 200
    refused = await flow.client.post(f"/api/game-matches/{match_id}/keep-both")
    assert refused.status_code == 409
