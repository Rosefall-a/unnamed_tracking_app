"""Protected-title regressions through real auth, HTTP routes and PostgreSQL."""

import asyncio
import time
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from src.core.auth import hash_password, hash_token, session_cookie_name
from src.database.models.anime import Anime
from src.database.models.auth import UserSession
from src.database.models.game import Game
from src.database.models.movies import Movie
from src.database.models.tv_show import TVShow
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features.metadata.locked_fields import apply_metadata_updates
from src.main import app

MODELS = {"game": Game, "movie": Movie, "tv": TVShow, "anime": Anime}


@pytest.fixture(params=MODELS)
async def library(request):
    kind = request.param
    model = MODELS[kind]
    username = f"protection_{uuid4().hex}"
    async with SessionLocal() as db:
        user = User(
            username=username,
            email=f"{username}@example.test",
            password_hash=hash_password("Test-password!9"),
            is_admin=True,
        )
        db.add(user)
        await db.flush()
        row = model(
            user_id=user.id,
            title="Original",
            sort_title="original",
            description="Keep description",
            locked_fields=["description"],
        )
        if kind == "game":
            row.folder_location = username
        db.add(row)
        await db.commit()
        user_id, entity_id = user.id, row.id
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as ui:
        login = await ui.post(
            "/api/auth/login", json={"username_or_email": username, "password": "Test-password!9"}
        )
        assert login.status_code == 200, login.text
        key = await ui.post(
            "/api/auth/api-keys", json={"name": "API client", "scopes": ["api.full"]}
        )
        assert key.status_code == 200, key.text
        token = key.json()["api_key"]
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            headers={"Authorization": f"Bearer {token}"},
        ) as api:
            yield SimpleNamespace(
                kind=kind,
                model=model,
                id=entity_id,
                user_id=user_id,
                ui=ui,
                api=api,
                path=f"/api/{kind}/update/{entity_id}",
            )
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def read_row(library):
    async with SessionLocal() as db:
        return await db.scalar(select(library.model).where(library.model.id == library.id))


async def protect(library):
    response = await library.ui.patch(library.path, json={"title_lock": True})
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Original"
    assert set(response.json()["locked_fields"]) == {"title", "description"}


async def metadata_refresh(library):
    async with SessionLocal() as db:
        row = await db.scalar(
            select(library.model).where(library.model.id == library.id).with_for_update()
        )
        apply_metadata_updates(
            row,
            {
                "title": "Provider title",
                "sort_title": "provider title",
                "description": "Provider description",
            },
        )
        await db.commit()


async def test_ui_protects_unchanged_title_and_metadata_preserves_it(library):
    await protect(library)
    await metadata_refresh(library)
    row = await read_row(library)
    assert (row.title, row.sort_title, row.description) == (
        "Original",
        "original",
        "Keep description",
    )


@pytest.mark.parametrize("explicit", [False, True])
async def test_ui_edit_locks_and_can_edit_again_without_unlocking(library, explicit):
    body = {"title": "Manual title", "description": "Manual description"}
    if explicit:
        body["title_lock"] = True
    response = await library.ui.patch(library.path, json=body)
    assert response.status_code == 200, response.text
    assert set(response.json()["locked_fields"]) == {"title", "description"}
    response = await library.ui.patch(library.path, json={"title": "Second manual title"})
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Second manual title"
    assert "title" in response.json()["locked_fields"]


@pytest.mark.parametrize("edit", [False, True])
async def test_ui_unlock_is_atomic_and_allows_later_metadata(library, edit):
    await protect(library)
    body = {"title_lock": False}
    if edit:
        body["title"] = "Unlocked custom title"
    response = await library.ui.patch(library.path, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["locked_fields"] == ["description"]
    assert response.json()["title"] == ("Unlocked custom title" if edit else "Original")
    await metadata_refresh(library)
    assert (await read_row(library)).title == "Provider title"


async def test_omitted_lock_and_unchanged_title_preserve_protection(library):
    await protect(library)
    for client in (library.ui, library.api):
        response = await client.patch(library.path, json={"title": "Original", "favorite": True})
        assert response.status_code == 200, response.text
        assert set(response.json()["locked_fields"]) == {"title", "description"}


@pytest.mark.parametrize(
    "body",
    [
        {"title": "API title"},
        {"title_lock": False},
        {"title_lock": True},
        {"title": "API title", "title_lock": False},
        {"title": "API title", "title_lock": True},
        {"title": "API title", "locked_fields": []},
        {"title": "API title", "title_lock": False, "is_ui": True},
    ],
)
async def test_api_cannot_edit_or_manage_protected_title_even_with_ui_headers(library, body):
    await protect(library)
    # Valid UI cookies alongside an API key must not elevate the chosen credential.
    library.api.cookies.update(library.ui.cookies)
    response = await library.api.patch(
        library.path,
        json={"favorite": True, **body},
        headers={
            "User-Agent": "Mozilla/5.0",
            "Origin": "http://testserver",
            "Referer": "http://testserver/",
            "X-Is-UI": "true",
            "is_ui": "true",
            "X-Interactive-Session": "true",
        },
    )
    assert response.status_code == 403, response.text
    row = await read_row(library)
    assert row.title == "Original" and not row.favorite
    assert set(row.locked_fields) == {"title", "description"}


async def test_api_unprotected_edit_remains_usable_and_automatically_locks(library):
    response = await library.api.patch(library.path, json={"title": "API title"})
    assert response.status_code == 200, response.text
    assert set(response.json()["locked_fields"]) == {"title", "description"}
    assert (await library.api.patch(library.path, json={"title": "Next title"})).status_code == 403


@pytest.mark.parametrize("locked", [True, False])
async def test_api_cannot_explicitly_manage_even_unprotected_title(library, locked):
    response = await library.api.patch(library.path, json={"title_lock": locked})
    assert response.status_code == 403, response.text
    assert (await read_row(library)).locked_fields == ["description"]


@pytest.mark.parametrize("value", [None, "false", 0, 1])
async def test_protection_requires_a_json_boolean(library, value):
    response = await library.ui.patch(library.path, json={"title_lock": value})
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("credential", ["utpm_management", "pm1.session.runtime-credential"])
async def test_plugin_credentials_cannot_use_application_title_updates(library, credential):
    await protect(library)
    response = await library.ui.patch(
        library.path,
        json={"title": "Plugin", "title_lock": False},
        headers={"Authorization": f"Bearer {credential}"},
    )
    assert response.status_code in {401, 403}, response.text
    assert (await read_row(library)).title == "Original"


@pytest.mark.parametrize("invalid_session", ["expired", "revoked", "forged"])
async def test_invalid_browser_session_is_not_authorized(library, invalid_session):
    await protect(library)
    cookie_name = session_cookie_name("testserver")
    token = library.ui.cookies.get(cookie_name)
    if invalid_session == "forged":
        library.ui.cookies.clear()
        library.ui.cookies.set(cookie_name, "forged")
    else:
        async with SessionLocal() as db:
            session = await db.scalar(
                select(UserSession).where(UserSession.token_hash == hash_token(token))
            )
            if invalid_session == "expired":
                session.expires_at = int(time.time()) - 1
            else:
                session.revoked_at = int(time.time())
            await db.commit()
    response = await library.ui.patch(library.path, json={"title_lock": False})
    assert response.status_code == 401, response.text


async def test_concurrent_api_edit_waits_for_protection_then_rejects(library):
    async with SessionLocal() as db:
        row = await db.scalar(
            select(library.model).where(library.model.id == library.id).with_for_update()
        )
        row.locked_fields = ["description", "title"]
        await db.flush()
        pending = asyncio.create_task(
            library.api.patch(library.path, json={"title": "Race bypass"})
        )
        await asyncio.sleep(0.1)
        assert not pending.done()
        await db.commit()
        response = await asyncio.wait_for(pending, timeout=5)
    assert response.status_code == 403, response.text
    assert (await read_row(library)).title == "Original"


def test_openapi_exposes_only_the_four_update_controls():
    schemas = app.openapi()["components"]["schemas"]
    for name in ("Game", "Movie", "TVShow", "Anime"):
        assert schemas[f"{name}Update"]["properties"]["title_lock"]["type"] == "boolean"
        assert "title_lock" not in schemas[f"{name}Create"]["properties"]
