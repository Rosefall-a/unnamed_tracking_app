"""Exercise the production import, refresh, and plugin gateway mutation paths."""

import time
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from src.api.routes import games, library_sync
from src.api.routes.plugin_manager import runtime
from src.core.auth import hash_password
from src.core.titles import display_title
from src.database.models.anime import Anime, AnimeSeason
from src.database.models.game import Game
from src.database.models.movies import Movie
from src.database.models.plugin_permissions import PluginPermissionGrant
from src.database.models.tv_show import TVShow
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features.imports.anilist import import_anilist_library
from src.features.metadata.anime.anilist_import import AniListImportClient, _map_entry
from src.main import app
from src.plugin_api.media_sync import ResolvedSync, dispatch_media_sync


@pytest.fixture
async def owner():
    async with SessionLocal() as db:
        user = User(
            username=f"source_{uuid4().hex}",
            email=f"{uuid4()}@example.test",
            password_hash=hash_password("Test-password!9"),
        )
        db.add(user)
        await db.commit()
        identity = user.id
    yield identity
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == identity))
        await db.commit()


@pytest.mark.parametrize(
    ("locked_fields", "provider_title"),
    [(["title"], "Steam title"), ([], "My Steam title")],
)
async def test_game_library_resync_preserves_protected_or_unchanged_title(
    owner, locked_fields, provider_title
):
    async with SessionLocal() as db:
        game = Game(
            user_id=owner,
            title="My Steam title",
            sort_title="my sort",
            source="steam",
            external_id="123",
            folder_location=uuid4().hex,
            locked_fields=locked_fields,
        )
        db.add(game)
        await db.commit()
        found, created = await library_sync._get_or_create_game(
            db, owner, provider_title, "steam", "123"
        )
        assert not created and found.id == game.id
        await db.commit()
        await db.refresh(game)
        assert (game.title, game.sort_title, game.locked_fields) == (
            "My Steam title",
            "my sort",
            locked_fields,
        )


@pytest.mark.parametrize("http_import", [False, True])
async def test_anilist_manual_and_background_imports_respect_existing_locks(
    owner, monkeypatch, http_import
):
    entry = _map_entry(
        {
            "status": "COMPLETED",
            "score": 8,
            "progress": 12,
            "media": {
                "id": 123,
                "title": {"english": "Provider anime"},
                "description": "Provider description",
                "startDate": {},
                "episodes": 12,
                "genres": [],
                "studios": {"nodes": []},
                "coverImage": {},
            },
        }
    )
    monkeypatch.setattr(AniListImportClient, "fetch_user_anime", lambda *_: [entry])
    async with SessionLocal() as db:
        show = Anime(
            user_id=owner,
            title="My anime",
            sort_title="my sort",
            anilist_id="123",
            description="My description",
            locked_fields=["title", "description"],
            seasons=[AnimeSeason(season_number=1)],
        )
        db.add(show)
        await db.commit()
        identity = show.id
    if http_import:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            async with SessionLocal() as db:
                username = (await db.get(User, owner)).username
            assert (
                await client.post(
                    "/api/auth/login",
                    json={"username_or_email": username, "password": "Test-password!9"},
                )
            ).status_code == 200
            response = await client.post(
                "/api/anime/import/anilist",
                json={"username": "public-user", "update_existing": True},
            )
            assert response.status_code == 200, response.text
            result = response.json()
    else:
        async with SessionLocal() as db:
            result = await import_anilist_library(db, owner, "public-user", True)
    assert result["updated"] == 1, result
    async with SessionLocal() as db:
        show = await db.get(Anime, identity)
        assert (show.title, show.sort_title, show.description) == (
            "My anime",
            "my sort",
            "My description",
        )
        assert show.seasons[0].episodes_watched == 12
        assert set(show.locked_fields) == {"title", "description"}


async def test_game_refresh_endpoint_respects_protection_for_api_actor(
    owner, monkeypatch, tmp_path
):
    monkeypatch.setattr(games, "_DATA_ROOT", tmp_path)
    monkeypatch.setattr(
        games,
        "search_game_metadata",
        lambda *_: {
            "providers": ["Steam"],
            "results": [{"provider": "Steam", "title": "Original™", "developer": "New developer"}],
        },
    )
    async with SessionLocal() as db:
        game = Game(
            user_id=owner,
            title="Original",
            sort_title="original",
            folder_location=uuid4().hex,
            locked_fields=["title"],
        )
        db.add(game)
        await db.commit()
        identity = game.id
        username = (await db.get(User, owner)).username
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        await client.post(
            "/api/auth/login", json={"username_or_email": username, "password": "Test-password!9"}
        )
        key = (await client.post("/api/auth/api-keys", json={"name": "Refresh"})).json()["api_key"]
        response = await client.post(
            f"/api/game/{identity}/metadata/refresh",
            json={"fill_missing_art": False},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 200, response.text
        assert "title" in response.json()["skipped_locked_fields"]
    async with SessionLocal() as db:
        game = await db.get(Game, identity)
        assert game.title == "Original" and game.developer == "New developer"
        assert game.locked_fields == ["title"]


@pytest.mark.parametrize("kind,model", [("movie", Movie), ("tv_show", TVShow), ("anime", Anime)])
@pytest.mark.parametrize("capability", ["media.write", "api.full"])
async def test_plugin_gateway_rejects_protected_title_even_with_broad_grant(
    owner, monkeypatch, kind, model, capability
):
    installation = uuid4()
    monkeypatch.setenv("PLUGIN_RUNTIME_TOKEN", "runtime-test-secret")
    monkeypatch.setattr(
        runtime,
        "_live_plugin",
        AsyncMock(
            return_value={
                "api_contract_version": "1.1.0",
                "plugin_id": "test.title",
                "installation_id": str(installation),
                "enabled": True,
                "compatible": True,
                "status": "running",
                "health": "healthy",
            }
        ),
    )
    async with SessionLocal() as db:
        db.add(
            PluginPermissionGrant(
                plugin_id="test.title",
                installation_id=installation,
                capability=capability,
                capability_version=1,
                user_id=owner,
                granted_at=int(time.time()),
            )
        )
        await db.commit()
        payload = {
            "source": "provider",
            "source_scope": "server",
            "external_id": "123",
            "media_type": kind,
            "title": "Original",
        }
        first = await dispatch_media_sync(
            db, plugin_id="test.title", user_id=owner, payload=payload
        )
        row = await db.get(model, first["id"])
        row.locked_fields = ["title"]
        await db.commit()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/plugins/runtime/gateway",
            headers={"X-Plugin-Runtime-Token": "runtime-test-secret"},
            json={
                "plugin_id": "test.title",
                "installation_id": str(installation),
                "request_id": str(uuid4()),
                "user_id": str(owner),
                "method": "media.sync",
                "capability": capability,
                "payload": {
                    **payload,
                    "title": "Plugin overwrite",
                    "expected_revision": first["revision"],
                },
            },
        )
        assert response.status_code == 403, response.text
    async with SessionLocal() as db:
        row = await db.get(model, first["id"])
        assert row.title == "Original" and row.locked_fields == ["title"]


@pytest.mark.parametrize("kind,model", [("movie", Movie), ("tv_show", TVShow), ("anime", Anime)])
async def test_plugin_metadata_enrichment_preserves_title_and_sort(owner, kind, model):
    async with SessionLocal() as db:
        row = model(user_id=owner, title="My title", sort_title="my sort", locked_fields=["title"])
        db.add(row)
        await db.commit()
        identity = row.id
        await dispatch_media_sync(
            db,
            plugin_id="provider.test",
            user_id=owner,
            payload={
                "source": "provider",
                "source_scope": "server",
                "external_id": "123",
                "media_type": kind,
                "title": "Provider title",
                "genres": ["Drama"],
            },
            options=ResolvedSync(identity=identity, enrich=True, update_watch=False),
        )
        await db.refresh(row)
        assert (row.title, row.sort_title, row.locked_fields) == ("My title", "my sort", ["title"])
        assert row.genres == ["Drama"]


def test_protected_anime_display_uses_custom_title():
    from types import SimpleNamespace

    show = SimpleNamespace(
        title="My title", title_english="Provider", title_native="Other", locked_fields=["title"]
    )
    for language in ("english", "romaji", "native"):
        assert display_title(show, language) == "My title"
