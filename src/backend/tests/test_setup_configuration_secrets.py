"""The setup configuration never hands out the database password, and after setup
only an administrator can read it."""

import httpx

from src.core.env_handler import EnvConfigHandler
from src.main import app
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture, so an account exists)


def _field(name: str) -> dict:
    for section in EnvConfigHandler().setup_schema():
        for field in section["fields"]:
            if field["name"] == name:
                return field
    raise AssertionError(f"{name} is not in the setup schema")


def test_the_database_url_is_never_sent(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:hunter2@db:5432/app")
    field = _field("DATABASE_URL")
    assert field["secret"] is True
    assert field["value"] is None


def test_no_secret_field_carries_a_value(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:hunter2@db:5432/app")
    for section in EnvConfigHandler().setup_schema():
        for field in section["fields"]:
            if field["secret"]:
                assert field["value"] is None, field["name"]


async def test_an_anonymous_visitor_cannot_read_it_once_an_account_exists(flow) -> None:  # noqa: F811
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as anonymous:
        response = await anonymous.get("/api/setup/configuration")
    assert response.status_code == 401
    assert "hunter2" not in response.text
