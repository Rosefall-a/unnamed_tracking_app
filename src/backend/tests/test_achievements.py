"""What a sync stores for each achievement reaches the achievements API.

Each test makes its own scratch user and deletes it afterwards (which
cascades to every game and achievement it made).
"""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from sqlalchemy import delete

from src.api.routes import games, library_sync
from src.api.schemas.game import GameCreate
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import SessionLocal


@pytest.fixture(autouse=True)
def no_game_folders(monkeypatch):
    monkeypatch.setattr(games, "create_game_folder", lambda *_args: None)


@pytest.fixture
async def scratch_user():
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        user_id = user.id
    yield SimpleNamespace(id=user_id)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def _game_with(user, provider: str, rows: list[dict]):
    async with SessionLocal() as db:
        game = await games.create_game(
            GameCreate(title="Hidden Test", folder_location="Hidden_Test"),
            Response(),
            db,
            user,
        )
        game_id = game.id
        await library_sync._replace_achievements(db, game_id, provider, rows)
        await db.commit()
    return game_id


async def _listed(user, game_id) -> dict[str, dict]:
    async with SessionLocal() as db:
        items = await games.list_game_achievements(game_id, db, user)
    return {item["name"]: item for item in items}


async def test_hidden_flag_is_stored_and_returned(scratch_user):
    game_id = await _game_with(
        scratch_user,
        "Steam",
        [
            {
                "external_id": "ACH_SECRET",
                "name": "A secret",
                "description": None,
                "icon_url": None,
                "unlocked": False,
                "unlocked_at": None,
                "hidden": True,
            },
            {
                "external_id": "ACH_PLAIN",
                "name": "A plain one",
                "description": "Do the thing.",
                "icon_url": "https://example.test/i.png",
                "unlocked": True,
                "unlocked_at": 1_700_000_000,
                "hidden": False,
            },
        ],
    )
    listed = await _listed(scratch_user, game_id)
    assert listed["A secret"]["hidden"] is True
    assert listed["A plain one"]["hidden"] is False


async def test_a_row_with_no_flag_is_not_hidden(scratch_user):
    """RetroAchievements sends no hidden flag at all, so its rows rely on the
    column's default."""
    game_id = await _game_with(
        scratch_user,
        "RetroAchievements",
        [
            {
                "external_id": "1",
                "name": "Retro one",
                "description": "Beat the level.",
                "icon_url": None,
                "unlocked": False,
                "unlocked_at": None,
            }
        ],
    )
    assert (await _listed(scratch_user, game_id))["Retro one"]["hidden"] is False


async def test_tier_is_returned_for_retroachievements(scratch_user):
    game_id = await _game_with(
        scratch_user,
        "RetroAchievements",
        [
            {
                "external_id": "7",
                "name": "Do not miss this",
                "description": "Missable.",
                "icon_url": None,
                "unlocked": False,
                "unlocked_at": None,
                "tier": "missable",
            }
        ],
    )
    assert (await _listed(scratch_user, game_id))["Do not miss this"]["tier"] == "missable"


async def test_a_resync_updates_the_flag_in_place(scratch_user):
    """Rows are upserted, so an achievement that gets hidden later updates the
    existing row instead of adding a second one."""
    row = {
        "external_id": "ACH_LATER",
        "name": "Hidden later",
        "description": None,
        "icon_url": None,
        "unlocked": False,
        "unlocked_at": None,
        "hidden": False,
    }
    game_id = await _game_with(scratch_user, "Steam", [row])
    async with SessionLocal() as db:
        await library_sync._replace_achievements(db, game_id, "Steam", [{**row, "hidden": True}])
        await db.commit()
    listed = await _listed(scratch_user, game_id)
    assert len(listed) == 1
    assert listed["Hidden later"]["hidden"] is True


_SCHEMA = {
    "ACH_PLAIN": {
        "name": "ACH_PLAIN",
        "displayName": "Plain",
        "description": "Do the thing.",
        "icon": "https://example.test/plain.png",
        "icongray": "https://example.test/plain_gray.png",
        "hidden": 0,
    },
    "ACH_SECRET": {
        "name": "ACH_SECRET",
        "displayName": "Secret",
        "icon": "https://example.test/secret.png",
        "icongray": "https://example.test/secret_gray.png",
        "hidden": 1,
    },
}


def test_steam_rows_carry_the_hidden_flag_icon_percent_and_unlock_state():
    rows = {
        r["external_id"]: r
        for r in library_sync._steam_achievement_rows(
            _SCHEMA,
            [{"apiname": "ACH_PLAIN", "achieved": 1, "unlocktime": 1_700_000_000}],
            {"ACH_PLAIN": 61.25},
        )
    }
    assert rows["ACH_PLAIN"]["unlocked"] is True
    assert rows["ACH_PLAIN"]["unlocked_at"] == 1_700_000_000
    assert rows["ACH_PLAIN"]["icon_url"].endswith("plain.png")
    assert rows["ACH_PLAIN"]["hidden"] is False
    assert rows["ACH_PLAIN"]["global_percent"] == 61.25
    assert rows["ACH_SECRET"]["unlocked"] is False
    assert rows["ACH_SECRET"]["icon_url"].endswith("secret_gray.png")
    assert rows["ACH_SECRET"]["hidden"] is True
    assert rows["ACH_SECRET"]["global_percent"] is None


def test_a_hidden_unlocked_achievement_takes_its_description_from_the_player_list():
    """The schema leaves a hidden achievement's description out, but the
    player list has it once it's unlocked."""
    rows = {
        r["external_id"]: r
        for r in library_sync._steam_achievement_rows(
            _SCHEMA,
            [
                {
                    "apiname": "ACH_SECRET",
                    "achieved": 1,
                    "unlocktime": 1_700_000_000,
                    "description": "Found the shrine.",
                }
            ],
        )
    }
    assert rows["ACH_SECRET"]["description"] == "Found the shrine."
    assert rows["ACH_PLAIN"]["description"] == "Do the thing."


def test_a_locked_hidden_achievement_stays_without_a_description():
    rows = {r["external_id"]: r for r in library_sync._steam_achievement_rows(_SCHEMA, [])}
    assert rows["ACH_SECRET"]["description"] is None


_COMMUNITY_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><playerstats>
<achievements>
<achievement closed="0"><iconClosed><![CDATA[https://x/a.jpg]]></iconClosed>
<name><![CDATA[Marked]]></name>
<description><![CDATA[Pick up a Marker fragment &amp; run.]]></description>
<apiname><![CDATA[ach46]]></apiname></achievement>
<achievement closed="1"><name><![CDATA[Plain]]></name>
<description><![CDATA[]]></description>
<apiname><![CDATA[ach1]]></apiname></achievement>
</achievements></playerstats>"""


def test_community_descriptions_are_read_by_apiname(monkeypatch):
    from src.features.metadata.games import steam

    seen = {}

    def fake_get(url, params=None, timeout=None):
        seen["url"] = url
        return SimpleNamespace(
            status_code=200,
            text=_COMMUNITY_XML,
            content=_COMMUNITY_XML.encode(),
            headers={},
        )

    monkeypatch.setattr(steam.SESSION, "get", fake_get)
    monkeypatch.setattr(steam.time, "sleep", lambda _s: None)
    found = steam.get_community_descriptions("76561190000000000", 1693980)
    assert found == {"ach46": "Pick up a Marker fragment & run."}
    assert "76561190000000000/stats/1693980" in seen["url"]


def test_community_requests_retry_when_steam_says_to_slow_down(monkeypatch):
    from src.features.metadata.games import steam

    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        if len(calls) < 3:
            return SimpleNamespace(status_code=429, text="", content=b"", headers={})
        return SimpleNamespace(
            status_code=200,
            text=_COMMUNITY_XML,
            content=_COMMUNITY_XML.encode(),
            headers={},
        )

    monkeypatch.setattr(steam.SESSION, "get", fake_get)
    monkeypatch.setattr(steam.time, "sleep", lambda _s: None)
    assert steam.get_community_descriptions("1", 1) == {"ach46": "Pick up a Marker fragment & run."}
    assert len(calls) == 3


async def test_a_lookup_that_found_nothing_does_not_erase_a_stored_description(scratch_user):
    row = {
        "external_id": "ACH_KEEP",
        "name": "Keep me",
        "description": "Real text.",
        "icon_url": None,
        "unlocked": False,
        "unlocked_at": None,
    }
    game_id = await _game_with(scratch_user, "Steam", [row])
    async with SessionLocal() as db:
        await library_sync._replace_achievements(
            db, game_id, "Steam", [{**row, "description": None}]
        )
        await db.commit()
    assert (await _listed(scratch_user, game_id))["Keep me"]["description"] == "Real text."


def test_community_descriptions_are_empty_when_steam_refuses(monkeypatch):
    from src.features.metadata.games import steam

    monkeypatch.setattr(
        steam.SESSION,
        "get",
        lambda *a, **k: SimpleNamespace(status_code=403, text="", content=b"", headers={}),
    )
    monkeypatch.setattr(steam.time, "sleep", lambda _s: None)
    assert steam.get_community_descriptions("1", 1) == {}


def test_hidden_achievements_take_their_description_from_the_community_feed():
    rows = {
        r["external_id"]: r
        for r in library_sync._steam_achievement_rows(
            _SCHEMA, [], None, {"ach_secret": "Open the door."}
        )
    }
    assert rows["ACH_SECRET"]["description"] == "Open the door."
    assert rows["ACH_PLAIN"]["description"] == "Do the thing."


def test_the_feed_matches_the_schema_whatever_the_case():
    """Steam's feed says `ach00` where the schema says `ACH00`: Elden Ring and
    many other games differ this way, so nothing matched until case was ignored."""
    schema = {
        "ACH00": {"name": "ACH00", "displayName": "Elden Lord", "hidden": 1},
    }
    rows = library_sync._steam_achievement_rows(schema, [], None, {"ach00": "Reach the end."})
    assert rows[0]["description"] == "Reach the end."


def test_the_community_feed_is_only_asked_for_when_a_hidden_description_is_missing():
    assert library_sync._needs_community_descriptions(_SCHEMA) is True
    assert library_sync._needs_community_descriptions({"A": {"name": "A", "hidden": 0}}) is False
    assert (
        library_sync._needs_community_descriptions(
            {"A": {"name": "A", "hidden": 1, "description": "Known."}}
        )
        is False
    )


def test_steam_rows_leave_the_percent_alone_when_none_were_fetched():
    """A full sync doesn't fetch percentages, and must not wipe stored ones."""
    rows = library_sync._steam_achievement_rows(_SCHEMA, [])
    assert all("global_percent" not in r for r in rows)


def test_retroachievements_rows_have_time_tier_and_the_share_of_players():
    rows = library_sync._retro_achievement_rows(
        {
            "NumDistinctPlayers": 200,
            "Achievements": {
                "11": {
                    "Title": "Beat it",
                    "Description": "Finish the game.",
                    "BadgeName": "12345",
                    "DateEarned": "2023-05-02 14:03:00",
                    "NumAwarded": 50,
                    "Type": "win_condition",
                },
                "12": {"Title": "Missed", "NumAwarded": 10, "type": "Missable"},
            },
        }
    )
    by_id = {r["external_id"]: r for r in rows}
    assert by_id["11"]["unlocked"] is True
    assert by_id["11"]["unlocked_at"] == 1_683_036_180
    assert by_id["11"]["tier"] == "win_condition"
    assert by_id["11"]["global_percent"] == 25.0
    assert by_id["11"]["icon_url"].endswith("/Badge/12345.png")
    assert by_id["12"]["unlocked"] is False
    assert by_id["12"]["unlocked_at"] is None
    assert by_id["12"]["tier"] == "missable"
    assert by_id["12"]["global_percent"] == 5.0


def test_playstation_rows_have_time_hidden_flag_and_earned_rate():
    rows = library_sync._psn_trophy_rows(
        [
            {
                "trophyId": 0,
                "trophyName": "First",
                "trophyDetail": "Start.",
                "trophyIconUrl": "https://example.test/t.png",
                "earned": True,
                "earnedDateTime": "2023-05-02T14:03:00Z",
                "trophyHidden": False,
                "trophyEarnedRate": "88.9",
            },
            {"trophyId": 1, "trophyName": "Secret", "trophyHidden": True},
            {"trophyName": "no id, skipped"},
        ]
    )
    assert len(rows) == 2
    assert rows[0]["unlocked_at"] == 1_683_036_180
    assert rows[0]["global_percent"] == 88.9
    assert rows[1]["hidden"] is True
    assert "global_percent" not in rows[1]


def test_unreadable_timestamps_are_none_not_an_error():
    assert library_sync._unix_from_text("") is None
    assert library_sync._unix_from_text(None) is None
    assert library_sync._unix_from_text("not a date") is None


async def _provider_game(user, *, source, external_id, platform=None):
    async with SessionLocal() as db:
        game = await games.create_game(
            GameCreate(title="Provider Test", folder_location="Provider_Test"),
            Response(),
            db,
            user,
        )
        row = await db.get(Game, game.id)
        row.source = source
        row.external_id = external_id
        row.platform = platform
        await db.commit()
        return game.id


def _creds(scratch_user, **extra):
    return SimpleNamespace(id=scratch_user.id, **extra)


async def _refresh(user, game_id):
    async with SessionLocal() as db:
        return await library_sync.refresh_game_achievements(game_id, db, user)


async def test_steam_refresh_stores_hidden_percent_and_unlock_state(scratch_user, monkeypatch):
    user = _creds(scratch_user, steam_id="76561190000000000", steam_api_key="key")
    game_id = await _provider_game(user, source="Steam", external_id="12345")
    monkeypatch.setattr(library_sync.steam, "resolve_steam_id", lambda sid, _key: sid)
    monkeypatch.setattr(library_sync.steam, "get_schema_for_game", lambda _key, _app: _SCHEMA)
    monkeypatch.setattr(
        library_sync.steam,
        "get_player_achievements",
        lambda *_args: [{"apiname": "ACH_PLAIN", "achieved": 1, "unlocktime": 1_700_000_000}],
    )
    monkeypatch.setattr(
        library_sync.steam, "get_global_percentages", lambda _app: {"ACH_SECRET": 1.8}
    )
    result = await _refresh(user, game_id)
    assert result == {"provider": "Steam", "achievements": 2, "unlocked": 1, "hidden": 1}
    listed = await _listed(user, game_id)
    assert listed["Secret"]["hidden"] is True
    assert listed["Secret"]["global_percent"] == 1.8
    assert listed["Plain"]["unlocked"] is True


async def test_retroachievements_refresh_uses_the_games_own_id(scratch_user, monkeypatch):
    user = _creds(scratch_user, retroachievements_username="me", retroachievements_api_key="k")
    game_id = await _provider_game(user, source="RetroAchievements", external_id="777")
    seen = {}

    def fake_progress(_self, username, game):
        seen["call"] = (username, game)
        return {
            "NumDistinctPlayers": 100,
            "Achievements": {"1": {"Title": "Only", "NumAwarded": 40, "Type": "progression"}},
        }

    monkeypatch.setattr(library_sync.RetroAchievementsClient, "get_game_progress", fake_progress)
    result = await _refresh(user, game_id)
    assert seen["call"] == ("me", "777")
    assert result["provider"] == "RetroAchievements"
    listed = await _listed(user, game_id)
    assert listed["Only"]["global_percent"] == 40.0
    assert listed["Only"]["tier"] == "progression"


async def test_playstation_refresh_falls_back_to_the_other_trophy_service(
    scratch_user, monkeypatch
):
    user = _creds(scratch_user, psn_npsso_token="enc")
    game_id = await _provider_game(user, source="PlayStation", external_id="NPWR1", platform="PS4")

    def trophies_for(np_id, service):
        if (np_id, service) == ("NPWR1", "trophy2"):
            return [{"trophyId": 0, "trophyName": "Got it", "earned": True}]
        return []

    monkeypatch.setattr(library_sync, "decrypt_secret", lambda _t: "npsso")
    monkeypatch.setattr(
        library_sync,
        "PSNClient",
        lambda _npsso: SimpleNamespace(get_trophies_for_title=trophies_for),
    )
    result = await _refresh(user, game_id)
    assert result["achievements"] == 1
    assert result["unlocked"] == 1


async def test_refresh_is_refused_for_a_game_from_another_source(scratch_user):
    game_id = await _provider_game(scratch_user, source="GOG", external_id="abc")
    with pytest.raises(HTTPException) as exc:
        await _refresh(_creds(scratch_user), game_id)
    assert exc.value.status_code == 400


async def test_refresh_needs_saved_credentials(scratch_user):
    game_id = await _provider_game(scratch_user, source="Steam", external_id="12345")
    with pytest.raises(HTTPException) as exc:
        await _refresh(_creds(scratch_user, steam_id=None, steam_api_key=None), game_id)
    assert exc.value.status_code == 400


async def test_an_empty_answer_does_not_wipe_stored_achievements(scratch_user, monkeypatch):
    user = _creds(scratch_user, steam_id="1", steam_api_key="key")
    game_id = await _provider_game(user, source="Steam", external_id="999")
    async with SessionLocal() as db:
        await library_sync._replace_achievements(
            db,
            game_id,
            "Steam",
            [
                {
                    "external_id": "K",
                    "name": "Kept",
                    "description": None,
                    "icon_url": None,
                    "unlocked": True,
                    "unlocked_at": 1,
                }
            ],
        )
        await db.commit()
    monkeypatch.setattr(library_sync.steam, "resolve_steam_id", lambda sid, _key: sid)
    monkeypatch.setattr(library_sync.steam, "get_schema_for_game", lambda _key, _app: {})
    result = await _refresh(user, game_id)
    assert result["achievements"] == 0
    assert "Kept" in await _listed(user, game_id)
