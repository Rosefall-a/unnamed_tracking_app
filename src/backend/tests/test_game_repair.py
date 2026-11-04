"""Filling in what a game is missing: only ever adds, finds art at the address
Steam really uses, never saves another game's play time, and tries again when a
site did not answer."""

import time
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select

from src.api.routes import library_import
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features import jobs
from src.features.metadata.games import repair, time_to_beat
from src.features.metadata.games.hltb import HLTBClient, HLTBError
from src.features.metadata.games.igdb import IGDBClient
from src.helpers import game_art_download as art

_MAIN = {"time_to_beat_hours": 9.5}


def _entry(title, hours=9.5):
    return {"id": 1, "title": title, "time_to_beat_hours": hours}


@pytest.mark.parametrize(
    ("title", "listed", "expected"),
    [
        ("Celeste", "Celeste", _MAIN),
        ("Terraria™", "Terraria", _MAIN),
        ("The Witcher 3 Complete Edition", "The Witcher 3", _MAIN),
        ("Celeste", "Celeste Classic", {}),
        ("BattleBit Remastered", "BattleBit", {}),
    ],
)
def test_a_saved_time_has_to_be_this_game(monkeypatch, title, listed, expected) -> None:
    monkeypatch.setattr(HLTBClient, "search", lambda _s, _t, limit=5: [_entry(listed)])
    assert HLTBClient().find_times(title, exact=True) == expected


def test_the_search_list_still_takes_its_best_guess(monkeypatch) -> None:
    monkeypatch.setattr(HLTBClient, "search", lambda _s, _t, limit=5: [_entry("Celeste Classic")])
    assert HLTBClient().find_times("Celeste") == _MAIN


def test_igdb_is_only_asked_while_howlongtobeat_is_down(monkeypatch) -> None:
    def down(_s, _title, exact=False):
        raise HLTBError("blocked")

    monkeypatch.setattr(IGDBClient, "play_times", lambda _s, _t: {"time_to_beat_hours": 4.0})

    monkeypatch.setattr(HLTBClient, "find_times", lambda _s, _t, exact=False: {})
    lookup = time_to_beat.TimesLookup("id", "secret")
    assert lookup.find("Not On The Site") == {}
    assert lookup.hltb_error is None

    monkeypatch.setattr(HLTBClient, "find_times", down)
    assert lookup.find("Anything") == {"time_to_beat_hours": 4.0}
    assert lookup.hltb_error == "blocked"


def test_store_art_uses_the_hashed_address_steam_gives(monkeypatch) -> None:
    assets = {
        "asset_url_format": "steam/apps/7/${FILENAME}?t=1",
        "library_capsule": "abc/library_capsule.jpg",
        "library_hero": "def/library_hero.jpg",
        "community_icon": "f00",
    }

    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": {"store_items": [{"assets": assets}]}}

    monkeypatch.setattr(art.requests, "get", lambda *_a, **_k: Reply())
    urls = art.steam_store_art_urls(7)
    assert urls["key_art"].endswith("/store_item_assets/steam/apps/7/abc/library_capsule.jpg?t=1")
    assert urls["banner"].endswith("/store_item_assets/steam/apps/7/def/library_hero.jpg?t=1")
    assert urls["icon"].endswith("/images/apps/7/f00.jpg")


def test_store_art_is_empty_when_steam_does_not_answer(monkeypatch) -> None:
    def refused(*_a, **_k):
        raise art.requests.ConnectionError("no")

    monkeypatch.setattr(art.requests, "get", refused)
    assert art.steam_store_art_urls(7) == {}


@pytest.fixture
def art_sources(monkeypatch):
    tried = []
    state = SimpleNamespace(tried=tried, works=set())

    async def download(url, _game_id, _kind):
        tried.append(url)
        return url in state.works

    class Client:
        def __init__(self, _key):
            pass

        def get_game_by_steam_appid(self, _app_id):
            return {"id": 5}

        def get_game_images(self, _game_id, image_type):
            return [SimpleNamespace(url=f"sgdb-{image_type}")]

    monkeypatch.setattr(art, "download_asset", download)
    monkeypatch.setattr(art, "SteamGridDBClient", Client)
    monkeypatch.setattr(
        art, "steam_store_art_urls", lambda _a: {"key_art": "store-cover", "icon": "steam-icon"}
    )
    return state


async def test_a_cover_falls_back_from_the_fixed_address_to_the_store(art_sources) -> None:
    art_sources.works = {"store-cover"}
    assert await art.fill_art(uuid.uuid4(), ["key_art"], 7, "Game", "key") == ["key_art"]
    assert art_sources.tried[-1] == "store-cover"
    assert len(art_sources.tried) == 2


async def test_an_icon_prefers_steamgriddb_over_steams_tiny_one(art_sources) -> None:
    art_sources.works = {"sgdb-icons", "steam-icon"}
    assert await art.fill_art(uuid.uuid4(), ["icon"], 7, "Game", "key") == ["icon"]
    assert art_sources.tried == ["sgdb-icons"]


async def test_nothing_found_saves_nothing(art_sources) -> None:
    assert await art.fill_art(uuid.uuid4(), ["key_art", "icon"], 7, "Game", "key") == []


def test_only_an_exact_name_counts_on_steamgriddb() -> None:
    class Client:
        def get_game_by_steam_appid(self, _app_id):
            raise art.SteamGridDBError("not found")

        def search_games(self, _query, limit=5):
            return [{"id": 1, "name": "Minecraft"}, {"id": 2, "name": "Minecraft: Dungeons II"}]

    assert art._steamgriddb_game_id(Client(), 7, "Minecraft Dungeons II") == 2
    assert art._steamgriddb_game_id(Client(), 7, "Minecraft Dungeons") is None
    # a placeholder is not a name to search for
    assert art._steamgriddb_game_id(Client(), 7, "Steam app 7") is None


def _settings(**overrides):
    values = {
        f"save_{field}": True
        for field in (
            "description", "developer", "publisher", "age_rating", "tags", "features",
            "release_date", "time_to_beat", "key_art", "banner", "logo", "icon",
        )
    }
    return SimpleNamespace(**{**values, **overrides})


def test_wanted_art_leaves_existing_locked_and_unwanted_alone(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(art, "DATA_ROOT", tmp_path)
    user_id = uuid.uuid4()
    folder = tmp_path / str(user_id) / "games" / "Game"
    folder.mkdir(parents=True)
    (folder / "key_art.png").write_bytes(b"mine")
    game = SimpleNamespace(user_id=user_id, folder_location="Game", locked_fields=["banner"])
    assert art.wanted_art(game, _settings(save_logo=False)) == ["icon"]
    assert (folder / "key_art.png").read_bytes() == b"mine"


@pytest.fixture
async def library(tmp_path, monkeypatch):
    monkeypatch.setattr(art, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(repair, "GAP_SECONDS", 0)
    saved_art = []

    async def fill(_game_id, kinds, *_a, **_k):
        saved_art.extend(kinds)
        return list(kinds)

    monkeypatch.setattr(repair, "fill_art", fill)
    monkeypatch.setattr(
        repair.steam,
        "get_app_details",
        lambda _app: {
            "name": "Real Name",
            "about_the_game": "From the store",
            "developers": ["Store Dev"],
            "release_date": {"date": "Mar 4, 2021"},
        },
    )
    monkeypatch.setattr(
        time_to_beat.HLTBClient, "find_times", lambda _s, _t, exact=False: dict(_MAIN)
    )
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        user_id = user.id

    async def add(**fields):
        name = uuid.uuid4().hex[:12]
        values = {"title": name, "sort_title": name, "folder_location": name, "source": "Steam", **fields}
        async with SessionLocal() as db:
            game = Game(user_id=user_id, **values)
            db.add(game)
            await db.commit()
            return game.id

    async def read(game_id):
        async with SessionLocal() as db:
            return await db.get(Game, game_id)

    yield SimpleNamespace(user_id=user_id, add=add, read=read, saved_art=saved_art)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def test_a_placeholder_game_gets_its_name_details_art_and_time(library) -> None:
    game_id = await library.add(title="Steam app 7", sort_title="steam app 7", external_id="7")
    result = await repair.repair_user_games(library.user_id)
    game = await library.read(game_id)
    assert (game.title, game.sort_title) == ("Real Name", "real name")
    assert game.description == "From the store"
    assert game.developer == "Store Dev"
    assert str(game.release_date) == "2021-03-04"
    assert float(game.time_to_beat_hours) == 9.5
    assert game.details_checked_at is not None
    assert set(library.saved_art) == {"key_art", "banner", "logo", "icon"}
    assert (result.checked, result.names, result.art, result.times) == (1, 1, 4, 1)


async def test_nothing_someone_wrote_or_locked_is_replaced(library) -> None:
    game_id = await library.add(
        title="My Name",
        sort_title="my name",
        external_id="7",
        developer="Written By Me",
        time_to_beat_hours=1.5,
        locked_fields=["description", "time_to_beat_extras_hours"],
    )
    await repair.repair_user_games(library.user_id)
    game = await library.read(game_id)
    assert game.title == "My Name"
    assert game.developer == "Written By Me"
    assert game.description is None
    assert float(game.time_to_beat_hours) == 1.5


async def test_a_locked_placeholder_name_stays(library) -> None:
    game_id = await library.add(title="Steam app 7", external_id="7", locked_fields=["title"])
    await repair.repair_user_games(library.user_id)
    assert (await library.read(game_id)).title == "Steam app 7"


async def test_howlongtobeat_being_down_loses_nothing_and_is_tried_again(
    library, monkeypatch
) -> None:
    def down(_s, _title, exact=False):
        raise HLTBError("blocked")

    monkeypatch.setattr(time_to_beat.HLTBClient, "find_times", down)
    monkeypatch.setattr(
        time_to_beat, "settings", SimpleNamespace(IGDB_CLIENT_ID=None, IGDB_CLIENT_SECRET=None)
    )
    monkeypatch.setattr(repair, "resolve_integrations", lambda _row: SimpleNamespace(
        igdb_client_id=None, igdb_client_secret=None
    ))
    kept = await library.add(external_id="7", developer="Dev", description="d", time_to_beat_all_hours=3)
    result = await repair.repair_user_games(library.user_id)
    game = await library.read(kept)
    assert result.hltb_error == "blocked"
    assert float(game.time_to_beat_all_hours) == 3
    assert game.details_checked_at is None  # so the next run asks about it again


async def test_steam_failing_on_one_game_is_tried_again(library, monkeypatch) -> None:
    def fails(_app):
        raise RuntimeError("busy")

    monkeypatch.setattr(repair.steam, "get_app_details", fails)
    game_id = await library.add(title="Steam app 7", external_id="7")
    result = await repair.repair_user_games(library.user_id)
    game = await library.read(game_id)
    assert game.title == "Steam app 7"
    assert game.details_checked_at is None
    assert result.failed == 0


async def test_a_game_checked_recently_is_left_until_the_recheck(library) -> None:
    now = int(time.time())
    fresh = await library.add(external_id="7", details_checked_at=now - 60)
    due = await library.add(external_id="8", details_checked_at=now - repair.RECHECK_SECONDS - 1)
    named = await library.add(title="Steam app 9", external_id="9", details_checked_at=now - 60)
    settings = _settings()
    assert not repair.needs_repair(await library.read(fresh), settings, now)
    assert repair.needs_repair(await library.read(due), settings, now)
    # a placeholder name is always worth asking about
    assert repair.needs_repair(await library.read(named), settings, now)


async def test_one_game_failing_does_not_stop_the_others(library, monkeypatch) -> None:
    real = repair.repair_game
    first = await library.add(external_id="7")
    second = await library.add(external_id="8")

    async def flaky(game, *args):
        if game.id == first:
            raise RuntimeError("broke")
        await real(game, *args)

    monkeypatch.setattr(repair, "repair_game", flaky)
    result = await repair.repair_user_games(library.user_id)
    assert result.failed == 1
    assert (await library.read(second)).details_checked_at is not None


async def test_someone_elses_games_are_not_touched(library) -> None:
    await library.add(external_id="7")
    result = await repair.repair_user_games(library.user_id)
    async with SessionLocal() as db:
        mine = (await db.scalars(select(Game).where(Game.user_id == library.user_id))).all()
    assert result.checked == len(mine) == 1


def test_the_new_jobs_stay_off_until_someone_turns_them_on() -> None:
    assert jobs.JOBS["steam_import"].default_enabled is False
    assert jobs.JOBS["game_repair"].default_enabled is False


async def test_the_scheduled_import_only_runs_saved_steam_accounts(monkeypatch) -> None:
    async with SessionLocal() as db:
        with_steam = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
            steam_id="1",
            steam_api_key="k",
        )
        without = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add_all([with_steam, without])
        await db.commit()
        ids = (with_steam.id, without.id)
    ran = []

    async def fake_run(user_id, provider, job):
        ran.append(user_id)
        if user_id == ids[0]:
            job.error = "Steam said no"
        else:
            job.result = {"games_added": 2}
        job.running = False

    monkeypatch.setattr(library_import, "_run", fake_run)
    try:
        out = await library_import.run_scheduled_steam_imports()
        assert ids[0] in ran
        assert ids[1] not in ran
        assert out["failed"] == 1
    finally:
        library_import._jobs.pop(ids[0], None)
        async with SessionLocal() as db:
            await db.execute(delete(User).where(User.id.in_(ids)))
            await db.commit()


def test_a_summary_says_when_howlongtobeat_did_not_answer() -> None:
    text = jobs.JOBS["game_repair"].summarize(
        {"checked": 3, "names": 1, "art": 2, "times": 0, "hltb_error": "blocked"}
    )
    assert "3 checked" in text
    assert "HowLongToBeat did not answer" in text
