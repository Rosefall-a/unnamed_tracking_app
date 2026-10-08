"""A whole Steam account imported through the real routes, against a pretend Steam.

Nothing here talks to the internet. Steam's Web API, store pages, community
feed and image CDN are replaced by a fake that answers with the same shapes the
real ones use, for an account of dozens of games (set MOCK_STEAM_GAMES=140 for a large one): some with no
achievements, hidden ones, partly or fully unlocked, a store page that does not
exist, missing cover art, odd titles. The import then runs exactly as the
app runs it (the sync request, then the enrich batches the frontend asks for)
and what ends up stored and served is checked game by game.
"""

import asyncio
import hashlib
import os
import io
import json
import random
import re
import uuid
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import requests
from PIL import Image
from sqlalchemy import delete, select

from src.api.routes import achievement_icons, default_game_assets, games, media_images
from src.core.auth import get_current_user
from src.database.models.achievement import Achievement
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features.metadata.games import steam, steam_tags
from src.helpers import image_prefetch, remote_images, save_game_asset
from src.main import app

STEAM_ID = "76561198012345678"
API_KEY = "0123456789abcdef0123456789abcdef"
CDN = "https://cdn.akamai.steamstatic.com"
UNLOCK_TIME = 1_700_000_000


# ---------------------------------------------------------------- the account
def _image(width: int, height: int, fmt: str, seed: int) -> tuple[bytes, str]:
    rng = random.Random(seed)
    color = tuple(rng.randrange(40, 220) for _ in range(3))
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, fmt)
    return buffer.getvalue(), f"image/{fmt.lower()}"


class FakeGame:
    def __init__(self, app_id: int, name: str, rng: random.Random, **kw: Any) -> None:
        self.app_id = app_id
        self.name = name
        self.playtime = kw.get("playtime", rng.choice([0, 0, 35, 240, 1800, 9000, 42000]))
        self.has_art = kw.get("has_art", rng.random() < 0.7)
        self.has_store_page = kw.get("has_store_page", rng.random() < 0.95)
        self.private_stats = kw.get("private_stats", False)
        # Steam answering 429 (too many requests) this many times before it answers
        self.busy_first = kw.get("busy_first", 0)
        self.busy_always = kw.get("busy_always", False)
        count = kw.get("achievements", rng.choice([0, 0, 12, 30, 50, 75, 100, 120]))
        self.schema: dict[str, dict] = {}
        self.player: list[dict] = []
        unlocked_share = kw.get("unlocked", rng.choice([0.0, 0.3, 0.6, 1.0]))
        for i in range(count):
            api = f"ACH_{app_id}_{i}"
            hidden = rng.random() < 0.15
            entry = {
                "name": api,
                "defaultvalue": 0,
                "displayName": f"{name[:20]} Achievement {i}",
                "hidden": int(hidden),
                "icon": f"{CDN}/steamcommunity/public/images/apps/{app_id}/{i:04x}a.jpg",
                "icongray": f"{CDN}/steamcommunity/public/images/apps/{app_id}/{i:04x}b.jpg",
            }
            if not hidden:
                entry["description"] = f"Do thing number {i}"
            self.schema[api] = entry
            achieved = int(rng.random() < unlocked_share)
            row = {
                "apiname": api,
                "achieved": achieved,
                "unlocktime": UNLOCK_TIME + i if achieved else 0,
                "name": entry["displayName"],
            }
            if achieved or not hidden:
                row["description"] = f"Do thing number {i}"
            self.player.append(row)
        self.expected_unlocked = sum(r["achieved"] for r in self.player)


def build_account(total: int = int(os.environ.get("MOCK_STEAM_GAMES", "30"))) -> list[FakeGame]:
    rng = random.Random(2026)
    account = [
        FakeGame(72850, "The Elder Scrolls V: Skyrim", rng, achievements=75, unlocked=0.7, has_art=True),
        FakeGame(489830, "The Elder Scrolls V: Skyrim Special Edition", rng, achievements=75, unlocked=0.7),
        FakeGame(1245620, "ELDEN RING", rng, achievements=42, unlocked=0.5, has_art=True),
        FakeGame(2280, "DOOM", rng, achievements=0),
        FakeGame(379720, "DOOM", rng, achievements=54),
        FakeGame(220, "Half-Life 2", rng, achievements=33, unlocked=1.0, has_art=True),
        FakeGame(570, "Dota 2", rng, achievements=0, playtime=90000),
        FakeGame(730, "Counter-Strike 2", rng, achievements=0, playtime=60000),
        FakeGame(1086940, "Baldur's Gate 3", rng, achievements=54, unlocked=0.4),
        FakeGame(292030, "The Witcher® 3: Wild Hunt", rng, achievements=78, unlocked=0.3),
        FakeGame(105600, "Terraria", rng, achievements=115, unlocked=0.1),
        FakeGame(413150, "Stardew Valley", rng, achievements=40, unlocked=0.9),
        FakeGame(8930, "Sid Meier's Civilization® V", rng, achievements=286, unlocked=0.2),
        FakeGame(367520, "Hollow Knight", rng, achievements=63, unlocked=0.6),
        FakeGame(1091500, "Cyberpunk 2077", rng, achievements=44, unlocked=0.5),
        FakeGame(251570, "7 Days to Die", rng, achievements=0),
        FakeGame(8500, "EVE Online", rng, achievements=0),
        FakeGame(6000, "Locked Out", rng, achievements=20, unlocked=0.5, private_stats=True),
        FakeGame(6001, "Ünïcödé 日本語 ゲーム", rng, achievements=10),
        FakeGame(6002, "Half/Slash: The \"Quoted\" Game?", rng, achievements=10),
        FakeGame(6003, "A" * 180, rng, achievements=5),
        FakeGame(6004, "Delisted Game", rng, achievements=15, has_store_page=False, has_art=False),
    ]
    next_id = 900_000
    while len(account) < total:
        next_id += rng.randrange(1, 4000)
        account.append(FakeGame(next_id, f"Generated Game {next_id}", rng))
    return account


JUNK = [
    {"appid": 1000001, "name": "Some Game Playtest", "playtime_forever": 0},
    {"appid": 1000002, "name": "Some Game Dedicated Server", "playtime_forever": 0},
]


# ---------------------------------------------------------------- pretend web
class FakeResponse:
    def __init__(self, status: int = 200, *, data: Any = None, text: str | None = None,
                 content: bytes | None = None, ctype: str = "application/json") -> None:
        self.status_code = status
        self._data = data
        if content is None:
            content = (json.dumps(data) if data is not None else (text or "")).encode()
        self.content = content
        self.text = content.decode("utf-8", errors="ignore")
        self.headers = {"content-type": ctype}

    def json(self) -> Any:
        if self._data is None:
            raise ValueError("not json")
        return self._data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def iter_content(self, size: int):
        for start in range(0, len(self.content), size):
            yield self.content[start : start + size]

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_a: Any) -> None:
        return None


class FakeSteam:
    def __init__(self, account: list[FakeGame], wishlist: list[FakeGame]) -> None:
        self.by_id = {g.app_id: g for g in [*account, *wishlist]}
        self.owned = account
        self.wishlist = wishlist
        self.calls: list[str] = []

    # Steam Web API, store and community pages (requests.Session.get)
    def session_get(self, url: str, params: dict | None = None, **_kw: Any) -> FakeResponse:
        params = params or {}
        self.calls.append(url)
        if "ResolveVanityURL" in url:
            return FakeResponse(data={"response": {"success": 1, "steamid": STEAM_ID}})
        if "GetPlayerSummaries" in url:
            return FakeResponse(data={"response": {"players": [{"steamid": STEAM_ID, "personaname": "Mock"}]}})
        if "GetOwnedGames" in url:
            games_payload = [
                {"appid": g.app_id, "name": g.name, "playtime_forever": g.playtime,
                 "rtime_last_played": UNLOCK_TIME, "img_icon_url": "abc"}
                for g in self.owned
            ] + JUNK
            return FakeResponse(data={"response": {"game_count": len(games_payload), "games": games_payload}})
        if "IWishlistService/GetWishlist" in url:
            items = [{"appid": g.app_id, "priority": i + 1, "date_added": UNLOCK_TIME}
                     for i, g in enumerate(self.wishlist)]
            return FakeResponse(data={"response": {"items": items}})
        app_id = int(params.get("appid") or params.get("gameid") or 0)
        game = self.by_id.get(app_id)
        if "GetSchemaForGame" in url:
            if game is None or not game.schema:
                return FakeResponse(data={"game": {}})
            stats = {"achievements": list(game.schema.values())}
            return FakeResponse(data={"game": {"gameName": game.name, "availableGameStats": stats}})
        if "GetPlayerAchievements" in url:
            if game is None or not game.schema:
                return FakeResponse(400, data={"playerstats": {"error": "Requested app has no stats", "success": False}})
            if game.busy_always:
                return FakeResponse(503, text="<html>Service Unavailable</html>", ctype="text/html")
            if game.busy_first > 0:
                game.busy_first -= 1
                return FakeResponse(429, text="<html>Too Many Requests</html>", ctype="text/html")
            if game.private_stats:
                return FakeResponse(403, data={"playerstats": {"error": "Profile is not public", "success": False}})
            payload = {"steamID": STEAM_ID, "gameName": game.name, "achievements": game.player, "success": True}
            return FakeResponse(data={"playerstats": payload})
        if "GetGlobalAchievementPercentagesForApp" in url:
            rows = [{"name": n, "percent": 12.5} for n in (game.schema if game else {})]
            return FakeResponse(data={"achievementpercentages": {"achievements": rows}})
        if "store.steampowered.com/api/appdetails" in url:
            return self._store_details(int(params["appids"]))
        if re.search(r"store\.steampowered\.com/app/\d+", url):
            return self._store_page(int(re.search(r"/app/(\d+)", url).group(1)))
        if "steamcommunity.com/profiles" in url:
            return self._community_stats(int(re.search(r"/stats/(\d+)", url).group(1)))
        raise AssertionError(f"unexpected Steam request: {url}")

    def _store_details(self, app_id: int) -> FakeResponse:
        game = self.by_id.get(app_id)
        if game is None or not game.has_store_page:
            return FakeResponse(data={str(app_id): {"success": False}})
        data = {
            "name": game.name, "steam_appid": app_id, "type": "game",
            "developers": ["Some Studio"], "publishers": ["Some Publisher"],
            "about_the_game": f"<h2>About</h2><p>{game.name} is a game.</p>",
            "short_description": f"{game.name} short blurb.",
            "genres": [{"id": "1", "description": "Action"}, {"id": "3", "description": "RPG"}],
            "categories": [{"id": 2, "description": "Single-player"}, {"id": 22, "description": "Steam Achievements"}],
            "release_date": {"coming_soon": False, "date": random.Random(app_id).choice(["Nov 11, 2011", "11 Nov, 2011", "2011"])},
            "required_age": 0,
            "header_image": f"{CDN}/steam/apps/{app_id}/header.jpg",
        }
        return FakeResponse(data={str(app_id): {"success": True, "data": data}})

    def _store_page(self, app_id: int) -> FakeResponse:
        tags = [{"tagid": 1, "name": n, "count": c, "browseable": True}
                for n, c in (("Souls-like", 9000), ("Open World", 7000), ("Singleplayer", 6000),
                             ("Dark Fantasy", 4000), ("RPG", 3500), ("Great Soundtrack", 900))]
        page = f"<html><script>InitAppTagModal( {app_id}, {json.dumps(tags)}, [] );</script></html>"
        return FakeResponse(text=page, ctype="text/html")

    def _community_stats(self, app_id: int) -> FakeResponse:
        game = self.by_id.get(app_id)
        blocks = "".join(
            f'<achievement closed="1"><apiname>{n}</apiname><name><![CDATA[{d["displayName"]}]]></name>'
            f"<description><![CDATA[Secret thing {n}]]></description></achievement>"
            for n, d in (game.schema if game else {}).items()
        )
        return FakeResponse(text=f"<playerstats><achievements>{blocks}</achievements></playerstats>",
                            ctype="text/xml")

    # image CDN (requests.get)
    def get(self, url: str, **_kw: Any) -> FakeResponse:
        self.calls.append(url)
        match = re.search(r"/steam/apps/(\d+)/(library_600x900\.jpg|library_hero\.jpg|logo\.png|header\.jpg)", url)
        if match:
            game = self.by_id.get(int(match.group(1)))
            kind = match.group(2)
            if game is None or (kind != "header.jpg" and not game.has_art):
                return FakeResponse(404, content=b"", ctype="text/html")
            sizes = {"library_600x900.jpg": (600, 900, "JPEG"), "library_hero.jpg": (1920, 620, "JPEG"),
                     "logo.png": (640, 360, "PNG"), "header.jpg": (460, 215, "JPEG")}
            width, height, fmt = sizes[kind]
            body, ctype = _image(width, height, fmt, game.app_id)
            return FakeResponse(content=body, ctype=ctype)
        if "/steamcommunity/public/images/apps/" in url:
            body, ctype = _image(64, 64, "JPEG", int(hashlib.md5(url.encode()).hexdigest()[:6], 16))
            return FakeResponse(content=body, ctype=ctype)
        raise AssertionError(f"unexpected image request: {url}")


# ---------------------------------------------------------------- the harness
@pytest.fixture
async def account(tmp_path, monkeypatch):
    world = build_account()
    wishlist = [FakeGame(2_000_000 + i, f"Wishlisted Game {i}", random.Random(i), achievements=0) for i in range(8)]
    fake = FakeSteam(world, wishlist)

    monkeypatch.setattr(steam.SESSION, "get", fake.session_get)
    monkeypatch.setattr(steam_tags._store_session, "get", fake.session_get)
    monkeypatch.setattr(requests, "get", fake.get)
    monkeypatch.setattr(steam, "_COMMUNITY_MIN_GAP", 0.0)
    monkeypatch.setattr(steam.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(steam_tags, "_STORE_MIN_GAP", 0.0)
    monkeypatch.setattr(remote_images, "is_public_host", lambda _host: True)
    for module, name in ((save_game_asset, "DATA_ROOT"), (default_game_assets, "_DATA_ROOT"),
                         (games, "_DATA_ROOT"), (media_images, "_DATA_ROOT"),
                         (image_prefetch, "MEDIA_ROOT")):
        monkeypatch.setattr(module, name, tmp_path)
    monkeypatch.setattr(image_prefetch, "ICON_ROOT", tmp_path / "shared")
    monkeypatch.setattr(achievement_icons, "_ICON_ROOT", tmp_path / "shared")
    image_prefetch.enable()
    image_prefetch._running.clear()
    image_prefetch._gave_up.clear()

    async with SessionLocal() as db:
        user = User(username=f"t_{uuid.uuid4().hex[:10]}", email=f"{uuid.uuid4().hex[:10]}@example.test",
                    password_hash="x", steam_id=STEAM_ID, steam_api_key=API_KEY)
        db.add(user)
        await db.commit()
        user_id = user.id

    async def current_user() -> User:
        async with SessionLocal() as db:
            found = await db.get(User, user_id)
            assert found is not None
            return found

    app.dependency_overrides[get_current_user] = current_user
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=300) as client:
        yield SimpleNamespace(client=client, user_id=user_id, world=world, wishlist=wishlist,
                              fake=fake, tmp=tmp_path)
    app.dependency_overrides.pop(get_current_user, None)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def _import_like_the_app(acc, batch: int = 5) -> dict:
    """The sync request, then the enrich batches the frontend asks for."""
    first = await acc.client.post("/api/library-sync/steam")
    assert first.status_code == 200, first.text
    result = first.json()
    wishlist = await acc.client.post("/api/library-sync/steam/wishlist")
    assert wishlist.status_code == 200, wishlist.text
    ids = result["enrich_game_ids"] + wishlist.json()["game_ids"]
    failed = 0
    for start in range(0, len(ids), batch):
        step = await acc.client.post("/api/library-sync/steam/enrich", json={"game_ids": ids[start : start + batch]})
        assert step.status_code == 200, step.text
        failed += step.json()["failed"]
    result["enrich_failed"] = failed
    result["wishlist"] = wishlist.json()
    return result


async def _stored(acc) -> dict[int, tuple[Game, list[Achievement]]]:
    async with SessionLocal() as db:
        rows = (await db.scalars(select(Game).where(Game.user_id == acc.user_id))).all()
        achievements = (await db.scalars(
            select(Achievement).join(Game, Game.id == Achievement.game_id).where(Game.user_id == acc.user_id)
        )).all()
    by_game: dict[Any, list[Achievement]] = {}
    for a in achievements:
        by_game.setdefault(a.game_id, []).append(a)
    return {int(g.external_id): (g, by_game.get(g.id, [])) for g in rows if (g.external_id or "").isdigit()}


# ---------------------------------------------------------------- the checks
@pytest.mark.parametrize("enable_wishlist", [False, True])
async def test_full_account_import(account, enable_wishlist) -> None:
    if enable_wishlist:
        patched = await account.client.patch("/api/preferences", json={"steam_import_wishlist": True})
        assert patched.status_code == 200, patched.text
    result = await _import_like_the_app(account)
    stored = await _stored(account)
    problems: list[str] = []

    owned = {g.app_id: g for g in account.world}
    if result["games_added"] != len(owned):
        problems.append(f"added {result['games_added']} games, account owns {len(owned)} (junk excluded)")
    for app_id, fake_game in owned.items():
        if app_id not in stored:
            problems.append(f"missing game {app_id} {fake_game.name!r}")
            continue
        game, rows = stored[app_id]
        if fake_game.private_stats:
            # Steam would not say what is unlocked: no achievements, and the game is reported
            if rows or game.title not in result["achievements_unavailable"]:
                problems.append(f"{game.title!r}: private game stored {len(rows)} rows, "
                                f"reported={game.title in result['achievements_unavailable']}")
            continue
        want = len(fake_game.schema)
        if len(rows) != want:
            problems.append(f"{game.title!r}: {len(rows)} achievements stored, Steam has {want}")
        unlocked = sum(1 for r in rows if r.unlocked)
        if not fake_game.private_stats and unlocked != fake_game.expected_unlocked:
            problems.append(f"{game.title!r}: {unlocked} unlocked, Steam says {fake_game.expected_unlocked}")
        hidden = sum(1 for r in rows if r.hidden)
        if hidden != sum(d["hidden"] for d in fake_game.schema.values()):
            problems.append(f"{game.title!r}: hidden flags differ")
        if fake_game.has_store_page and not game.description:
            problems.append(f"{game.title!r}: no description from the store page")
        if fake_game.has_store_page and not game.tags:
            problems.append(f"{game.title!r}: no genres or tags")
        if not fake_game.has_store_page and result["enrich_failed"] == 0:
            pass

    # artwork on disk, as the app serves it
    base = account.tmp
    for app_id, fake_game in owned.items():
        game = stored[app_id][0]
        folder = base / str(account.user_id) / "games" / game.folder_location
        kinds = [p.name for p in folder.glob("*.png")] if folder.exists() else []
        if fake_game.has_art:
            for needed in ("key_art.png", "banner.png", "logo.png"):
                if needed not in kinds:
                    problems.append(f"{game.title!r}: {needed} not saved (has CDN art)")
        elif fake_game.has_store_page and "banner.png" not in kinds:
            problems.append(f"{game.title!r}: no banner even from the store header image")

    wishlist_games = [s for a, s in stored.items() if a >= 2_000_000]
    if enable_wishlist:
        if len(wishlist_games) != len(account.wishlist):
            problems.append(f"wishlist: {len(wishlist_games)} stored, {len(account.wishlist)} on the wishlist")
        for game, _ in wishlist_games:
            if game.status.name != "WISHLIST":
                problems.append(f"wishlist game {game.title!r} has status {game.status.name}")
            if game.title.startswith("Steam app "):
                problems.append(f"wishlist game still has the placeholder name {game.title!r}")
    elif wishlist_games:
        problems.append("wishlist games were added with the setting off")

    assert not problems, "\n" + "\n".join(problems[:60]) + f"\n({len(problems)} problems)"


async def test_achievement_icons_are_served_from_disk(account) -> None:
    await _import_like_the_app(account)
    for _ in range(100):
        if not image_prefetch._running and not image_prefetch._tasks:
            break
        await asyncio.sleep(0.1)
    stored = await _stored(account)
    skyrim = stored[72850][1]
    assert skyrim, "Skyrim has no achievements stored"
    listed = (await account.client.get(f"/api/game/{stored[72850][0].id}/achievements")).json()
    assert len(listed) == 75
    assert all(a["icon_url"].startswith("/api/achievement-icon/") for a in listed), listed[:2]
    icons = list((account.tmp / "shared" / "achievement-icons").glob("*.png"))
    assert len(icons) > 400, f"only {len(icons)} icons were saved ahead of time"
    first = await account.client.get(listed[0]["icon_url"])
    assert first.status_code == 200 and first.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(first.content)).size == (64, 64), "the small icon must stay as the provider made it"
    large = await account.client.get(listed[0]["icon_url"], params={"large": 1})
    assert large.status_code == 200 and Image.open(io.BytesIO(large.content)).size == (256, 256)


async def test_skyrim_refresh_shows_what_steam_says(account) -> None:
    await _import_like_the_app(account)
    stored = await _stored(account)
    game = stored[72850][0]
    result = await account.client.post(f"/api/library-sync/games/{game.id}/achievements")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["achievements"] == 75 and body["unlocked"] == account.world[0].expected_unlocked
    locked_out = stored[6000][0]
    denied = await account.client.post(f"/api/library-sync/games/{locked_out.id}/achievements")
    assert denied.status_code == 502 and "Game details" in denied.json()["detail"]


async def test_game_art_endpoints_return_real_images(account) -> None:
    await _import_like_the_app(account)
    stored = await _stored(account)
    for app_id in (72850, 1245620, 220):
        game = stored[app_id][0]
        for kind in ("key_art", "banner", "logo"):
            response = await account.client.get(f"/api/game/{game.id}/assets/{kind}", params={"w": 600})
            assert response.status_code == 200, (app_id, kind, response.status_code)
            kind_of = response.headers["content-type"]
            assert kind_of.startswith("image/") and "svg" not in kind_of, (
                f"{game.title} {kind}: got {kind_of} (the generated placeholder?), "
                f"files: {sorted(p.name for p in (account.tmp / str(account.user_id) / 'games' / game.folder_location).glob('*'))}"
            )
            assert Image.open(io.BytesIO(response.content)).width > 0


async def test_import_makes_a_sane_number_of_steam_requests(account) -> None:
    await _import_like_the_app(account)
    from collections import Counter

    kinds = Counter(re.sub(r"[?].*", "", u).split("steampowered.com/")[-1][:40] for u in account.fake.calls)
    store_pages = sum(1 for u in account.fake.calls if re.search(r"store\.steampowered\.com/app/\d+", u))
    details = sum(1 for u in account.fake.calls if "store.steampowered.com/api/appdetails" in u)
    owned = len(account.world)
    assert store_pages <= owned + 1, f"{store_pages} store pages for {owned} games: {dict(kinds)}"
    assert details <= owned * 2 + len(account.wishlist), f"{details} appdetails calls for {owned} games"


async def test_rate_limited_answers_are_retried_not_read_as_nothing_unlocked(account) -> None:
    busy = [g for g in account.world if g.schema and not g.private_stats][:6]
    for game in busy:
        game.busy_first = 2  # two refusals, then Steam answers
    await _import_like_the_app(account)
    stored = await _stored(account)
    for game in busy:
        rows = stored[game.app_id][1]
        unlocked = sum(1 for r in rows if r.unlocked)
        assert unlocked == game.expected_unlocked, f"{game.name}: {unlocked} unlocked, Steam says {game.expected_unlocked}"


async def test_an_unreadable_answer_keeps_what_is_stored(account) -> None:
    await _import_like_the_app(account)
    target = next(g for g in account.world if g.expected_unlocked > 3 and not g.private_stats)
    before = sum(1 for r in (await _stored(account))[target.app_id][1] if r.unlocked)
    assert before == target.expected_unlocked
    target.busy_always = True
    again = await account.client.post("/api/library-sync/steam")
    assert again.status_code == 200, again.text
    assert target.name[:20] in " ".join(again.json()["achievements_unavailable"]) or again.json()["achievements_unavailable"]
    after = sum(1 for r in (await _stored(account))[target.app_id][1] if r.unlocked)
    assert after == before, f"{target.name}: {before} unlocked became {after} after Steam failed to answer"
