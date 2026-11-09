"""The server's own upload limit wins over one saved in the app, production nginx
lets real uploads through, and one calendar link can carry only part of the
calendar."""

from pathlib import Path
from secrets import token_urlsafe

import pytest

from src.core import app_integrations
from src.core.config import settings
from src.database.models.user import User
from src.database.session import SessionLocal
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)

_NGINX = Path(__file__).resolve().parents[2] / "docker-container" / "nginx"


@pytest.fixture
def env_limit(monkeypatch):
    monkeypatch.setattr(app_integrations, "upload_limit_is_from_environment", lambda: True)
    monkeypatch.setattr(
        "src.api.routes.settings.upload_limit_is_from_environment", lambda: True
    )
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 77)


async def test_the_environment_wins_and_cannot_be_changed_in_the_app(flow, env_limit) -> None:
    limits = (await flow.client.get("/api/settings/upload-limits")).json()
    assert limits["max_upload_size_mb"] == 77
    assert limits["from_environment"] is True
    assert limits["max_save_size_mb"] == settings.MAX_SAVE_ARCHIVE_SIZE_MB


@pytest.mark.skipif(not _NGINX.is_dir(), reason="the nginx files are not in this copy")
@pytest.mark.parametrize("conf", ["ready.conf", "readytls.conf", "readytlsredirect.conf"])
def test_production_nginx_lets_the_largest_upload_through(conf: str) -> None:
    text = (_NGINX / conf).read_text(encoding="utf-8")
    assert "client_max_body_size 4200m;" in text
    limit_mb = int(text.split("client_max_body_size ")[1].split("m;")[0])
    assert limit_mb >= settings.MAX_SAVE_ARCHIVE_SIZE_MB
    # one for each server block that proxies the API
    assert text.count("location /api/ {") == text.count("client_max_body_size")


async def test_the_feed_can_carry_only_some_kinds(flow) -> None:
    await flow.client.post(
        "/api/movie/create",
        json={"title": "Soon", "status": "WISHLIST", "release_date": "2099-01-01"},
    )
    await flow.client.post(
        "/api/calendar/events", json={"title": "Party", "event_date": "2099-01-01"}
    )
    async with SessionLocal() as db:
        (await db.get(User, flow.user_id)).calendar_token = token_urlsafe(16)
        await db.commit()
        path = f"/api/calendar/feed/{(await db.get(User, flow.user_id)).calendar_token}.ics"

    everything = (await flow.client.get(path)).text
    assert "Party" in everything

    only_tv = (await flow.client.get(path, params={"types": "tv"})).text
    assert "Party" not in only_tv
    assert "Soon" not in only_tv

    only_mine = (await flow.client.get(path, params={"types": "mine"})).text
    assert "Party" in only_mine
