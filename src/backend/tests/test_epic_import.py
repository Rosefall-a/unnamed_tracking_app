"""An Epic Games account connected and imported through the real routes,
against a pretend Epic: sign-in with a pasted code, a paged library holding
games, DLC and engine assets, playtime, catalog details and artwork. Nothing
here talks to the internet."""

import io
import json
import uuid
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import requests
from fastapi import Depends
from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes import epic_import
from src.core.auth import get_current_user
from src.database.models.game import Game, GameStatus
from src.database.models.user import User
from src.database.session import SessionLocal, get_db
from src.features.metadata.games import epic
from src.helpers import save_game_asset
from src.main import app

CODE = "0123456789abcdef0123456789abcdef"
ACCOUNT = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
CDN = "https://cdn1.epicgames.com"


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (60, 80), (90, 40, 160)).save(buffer, "PNG")
    return buffer.getvalue()


class Reply:
    def __init__(
        self,
        status: int = 200,
        data: Any = None,
        content: bytes | None = None,
        ctype: str = "application/json",
    ) -> None:
        self.status_code = status
        self._data = data
        self.content = content if content is not None else json.dumps(data).encode()
        self.headers = {"content-type": ctype}

    def json(self) -> Any:
        if self._data is None:
            raise ValueError("not json")
        return self._data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def _catalog_entry(item_id: str, title: str, *, dlc: bool = False, category: str = "games") -> dict:
    entry: dict[str, Any] = {
        "id": item_id,
        "title": title,
        "description": f"{title} blurb",
        "developer": "Some Studio",
        "seller": {"name": "Some Publisher"},
        "categories": [{"path": category}],
        "keyImages": [
            {"type": "DieselGameBoxTall", "url": f"{CDN}/{item_id}/tall.png"},
            {"type": "DieselGameBox", "url": f"{CDN}/{item_id}/wide.png"},
            {"type": "DieselGameBoxLogo", "url": f"{CDN}/{item_id}/logo.png"},
        ],
    }
    if dlc:
        entry["mainGameItem"] = {"id": "parent"}
    return entry


class FakeEpic:
    """Epic's token, library, playtime and catalog services, and its CDN."""

    def __init__(self, games: int = 30) -> None:
        self.records: list[dict] = []
        self.catalog: dict[str, dict] = {}
        self.playtime: dict[str, int] = {}
        for n in range(games):
            item_id = f"{n:032x}"
            namespace = f"ns{n:030x}"
            self.records.append(
                {
                    "namespace": namespace,
                    "catalogItemId": item_id,
                    "appName": f"App{n}",
                    "sandboxType": "PUBLIC",
                }
            )
            self.catalog[item_id] = _catalog_entry(item_id, f"Epic Game {n}")
            if n % 3 == 0:
                self.playtime[f"App{n}"] = 3600 * n
            if n % 5 == 0:
                # its DLC, in the same namespace
                dlc_id = f"d{n:031x}"
                self.records.append(
                    {
                        "namespace": namespace,
                        "catalogItemId": dlc_id,
                        "appName": f"App{n}Dlc",
                        "sandboxType": "PUBLIC",
                    }
                )
                self.catalog[dlc_id] = _catalog_entry(dlc_id, f"Epic Game {n} DLC", dlc=True)
        # never imported: an engine asset, a private sandbox, an add-on
        self.records.append({"namespace": "ue", "catalogItemId": "e" * 32, "appName": "UeAsset"})
        self.records.append(
            {
                "namespace": "nsx",
                "catalogItemId": "f" * 32,
                "appName": "Private",
                "sandboxType": "PRIVATE",
            }
        )
        self.records.append({"namespace": "nsy", "catalogItemId": "c" * 32, "appName": "Addon"})
        self.catalog["c" * 32] = _catalog_entry("c" * 32, "Some Add-on", category="addons/durable")
        self.refresh_tokens = {"refresh-0"}
        self.issued = 0
        self.token_calls = 0
        self.expired = False

    # requests.Session().post / .get
    def post(self, url: str, data: dict, **_kw: Any) -> Reply:
        assert "oauth/token" in url
        self.token_calls += 1
        if data["grant_type"] == "authorization_code" and data["code"] != CODE:
            return Reply(
                400,
                {"errorCode": "errors.com.epicgames.account.oauth.authorization_code_not_found"},
            )
        if data["grant_type"] == "refresh_token" and (
            self.expired or data["refresh_token"] not in self.refresh_tokens
        ):
            return Reply(
                400, {"errorCode": "errors.com.epicgames.account.auth_token.invalid_refresh_token"}
            )
        self.issued += 1
        token = f"refresh-{self.issued}"
        self.refresh_tokens = {token}
        return Reply(
            200,
            {
                "access_token": f"access-{self.issued}",
                "expires_in": 28800,
                "refresh_token": token,
                "account_id": ACCOUNT,
                "displayName": "EpicPlayer",
            },
        )

    def get(self, url: str, params: Any = None, headers: dict | None = None, **_kw: Any) -> Reply:
        assert (headers or {}).get("Authorization", "").startswith("bearer access-")
        if "/library/api/public/items" in url:
            cursor = int((params or {}).get("cursor") or 0)
            page = self.records[cursor : cursor + 10]
            meta = {"nextCursor": str(cursor + 10)} if cursor + 10 < len(self.records) else {}
            return Reply(200, {"records": page, "responseMetadata": meta})
        if "/playtime/account/" in url:
            assert ACCOUNT in url
            return Reply(
                200,
                [
                    {"accountId": ACCOUNT, "artifactId": a, "totalTime": t}
                    for a, t in self.playtime.items()
                ],
            )
        if "/bulk/items" in url:
            ids = [v for k, v in params if k == "id"]
            namespace = url.split("/namespace/")[1].split("/")[0]
            assert all(
                r["namespace"] == namespace for r in self.records if r["catalogItemId"] in ids
            )
            return Reply(200, {i: self.catalog[i] for i in ids if i in self.catalog})
        raise AssertionError(f"unexpected Epic request: {url}")


@pytest.fixture
async def acc(tmp_path, monkeypatch):
    fake = FakeEpic()
    monkeypatch.setattr(
        epic.requests, "Session", lambda: SimpleNamespace(headers={}, post=fake.post, get=fake.get)
    )

    def cdn(url: str, **_kw: Any) -> Reply:
        assert url.startswith(CDN), url
        return Reply(200, content=_png(), ctype="image/png")

    monkeypatch.setattr(requests, "get", cdn)
    monkeypatch.setattr(save_game_asset, "DATA_ROOT", tmp_path)
    epic_import._SESSIONS.clear()

    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        user_id = user.id

    # the request's own session, as the real dependency uses, so what a route
    # changes on the user is saved with its commit
    async def current_user(db: AsyncSession = Depends(get_db)) -> User:
        found = await db.get(User, user_id)
        assert found is not None
        return found

    app.dependency_overrides[get_current_user] = current_user
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", timeout=120
    ) as client:
        yield SimpleNamespace(client=client, user_id=user_id, fake=fake, tmp=tmp_path)
    app.dependency_overrides.pop(get_current_user, None)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def _import_like_the_app(acc) -> dict:
    """Sync steps, each continuing after the last, as the frontend runs them."""
    totals = {"games_added": 0, "steps": 0, "games": []}
    after = None
    while True:
        url = "/api/library-sync/epic" + (f"?after={after}" if after else "")
        reply = await acc.client.post(url)
        assert reply.status_code == 200, reply.text
        step = reply.json()
        totals["steps"] += 1
        totals["games_added"] += step["games_added"]
        totals["games"] += step["games"]
        if totals["steps"] == 1:
            totals["games_updated"] = step["games_updated"]
        if not step["next"]:
            totals["last"] = step
            return totals
        after = step["next"]


async def _games(acc) -> dict[str, Game]:
    async with SessionLocal() as db:
        rows = (await db.scalars(select(Game).where(Game.user_id == acc.user_id))).all()
    return {g.external_id: g for g in rows}


async def _connect(acc, code: str = CODE) -> httpx.Response:
    return await acc.client.post("/api/library-sync/epic/connect", json={"code": code})


@pytest.mark.parametrize(
    "pasted",
    [
        CODE,
        f'  "{CODE}"  ',
        json.dumps(
            {
                "warning": "x",
                "redirectUrl": f"https://localhost/launcher/authorized?code={CODE}",
                "authorizationCode": CODE,
                "exchangeCode": None,
                "sid": None,
            }
        ),
        json.dumps({"redirectUrl": f"https://localhost/launcher/authorized?code={CODE}"}),
        f"https://localhost/launcher/authorized?code={CODE}",
    ],
)
def test_the_code_is_found_in_whatever_was_copied(pasted) -> None:
    assert epic.extract_authorization_code(pasted) == CODE


def test_something_else_pasted_is_refused() -> None:
    with pytest.raises(epic.EpicError, match="authorization code"):
        epic.extract_authorization_code("my password")


async def test_connect_keeps_only_an_encrypted_refresh_token(acc) -> None:
    reply = await _connect(acc)
    assert reply.status_code == 200, reply.text
    assert reply.json() == {"status": "connected", "display_name": "EpicPlayer"}
    async with SessionLocal() as db:
        user = await db.get(User, acc.user_id)
        assert user.epic_account_id == ACCOUNT
        assert user.epic_refresh_token and "refresh-" not in user.epic_refresh_token
    status = (await acc.client.get("/api/settings/provider-credentials")).json()["Epic Games"]
    assert status["status"] == "configured"
    assert status["display_name"] == "EpicPlayer"
    assert status["library_games"] == 0


async def test_a_wrong_or_used_code_is_explained(acc) -> None:
    reply = await _connect(acc, "f" * 32)
    assert reply.status_code == 400
    assert "Codes work once" in reply.json()["detail"]


async def test_sync_needs_a_connection(acc) -> None:
    reply = await acc.client.post("/api/library-sync/epic")
    assert reply.status_code == 400
    assert "Connect your Epic Games account" in reply.json()["detail"]


async def test_full_library_import(acc) -> None:
    assert (await _connect(acc)).status_code == 200
    result = await _import_like_the_app(acc)
    games = await _games(acc)

    owned_games = [
        r
        for r in acc.fake.records
        if r["catalogItemId"] in acc.fake.catalog
        and epic.is_game(acc.fake.catalog[r["catalogItemId"]])
    ]
    assert result["games_added"] == len(owned_games) == len(games) == 30
    # a few new games per request, so the import took several
    assert result["steps"] == -(-30 // epic_import._NEW_PER_REQUEST)
    assert result["games_updated"] == 0
    for record in owned_games:
        game = games[record["catalogItemId"]]
        entry = acc.fake.catalog[record["catalogItemId"]]
        assert game.title == entry["title"]
        assert game.source == "Epic Games"
        assert game.developer == "Some Studio" and game.publisher == "Some Publisher"
        assert "Epic Games" in game.tags and "Epic Games" in game.collections
        seconds = acc.fake.playtime.get(record["appName"], 0)
        assert game.playtime_seconds == seconds
        assert game.status == (GameStatus.PLAYED if seconds else GameStatus.BACKLOG)
        folder = acc.tmp / str(acc.user_id) / "games" / game.folder_location
        assert {p.stem for p in folder.glob("*.png")} >= {"key_art", "banner", "logo"}, game.title
    titles = {g.title for g in games.values()}
    assert not any("DLC" in t or "Add-on" in t for t in titles)
    status = (await acc.client.get("/api/settings/provider-credentials")).json()["Epic Games"]
    assert status["library_games"] == 30 and status["last_synced_at"]


async def test_resync_updates_playtime_and_flags_what_left(acc) -> None:
    assert (await _connect(acc)).status_code == 200
    await _import_like_the_app(acc)
    gone = next(r for r in acc.fake.records if r["appName"] == "App1")
    acc.fake.records.remove(gone)
    acc.fake.playtime["App2"] = 7200
    token_calls = acc.fake.token_calls

    result = await _import_like_the_app(acc)
    assert result["steps"] == 1
    assert result["games_added"] == 0
    assert result["games_updated"] == 29
    assert result["last"]["games_flagged_stale"] == 1
    # the access token from the first import is reused, not traded again
    assert acc.fake.token_calls == token_calls
    games = await _games(acc)
    assert games[gone["catalogItemId"]].stale_since is not None
    assert games[f"{2:032x}"].playtime_seconds == 7200


async def test_an_expired_sign_in_asks_to_connect_again(acc) -> None:
    assert (await _connect(acc)).status_code == 200
    epic_import._SESSIONS.clear()
    acc.fake.expired = True
    reply = await acc.client.post("/api/library-sync/epic")
    assert reply.status_code == 400
    assert "connect Epic Games again" in reply.json()["detail"]


async def test_the_refresh_token_is_replaced_after_each_refresh(acc) -> None:
    assert (await _connect(acc)).status_code == 200
    epic_import._SESSIONS.clear()
    assert (await acc.client.post("/api/library-sync/epic")).status_code == 200
    epic_import._SESSIONS.clear()
    # Epic only honours the newest refresh token: the saved one must be it
    assert (await acc.client.post("/api/library-sync/epic")).status_code == 200


async def test_disconnect_keeps_the_games(acc) -> None:
    assert (await _connect(acc)).status_code == 200
    await _import_like_the_app(acc)
    reply = await acc.client.delete("/api/library-sync/epic/connect")
    assert reply.status_code == 200
    async with SessionLocal() as db:
        user = await db.get(User, acc.user_id)
        assert user.epic_refresh_token is None and user.epic_account_id is None
    assert len(await _games(acc)) == 30


def test_art_slots() -> None:
    entry = _catalog_entry("x" * 32, "X")
    assert set(epic.art_urls(entry)) == {"key_art", "banner", "logo"}
    only_thumb = {"keyImages": [{"type": "Thumbnail", "url": "u"}]}
    assert epic.art_urls(only_thumb) == {"key_art": "u"}


def test_login_url_points_at_epics_code_page() -> None:
    query = parse_qs(urlparse(epic.LOGIN_URL).query)
    assert "responseType=code" in query["redirectUrl"][0]
