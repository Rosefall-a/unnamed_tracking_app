"""Signed-in devices and "last used" times: noted at most every few minutes,
never in the way of a request, and signing out elsewhere keeps this browser."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.api.routes import auth as auth_routes
from src.core import auth as core_auth
from src.core.auth import hash_token, session_cookie_name


def _request(cookie: str | None = None) -> Request:
    headers = [(b"host", b"localhost")]
    if cookie is not None:
        name = session_cookie_name("localhost")
        headers.append((b"cookie", f"{name}={cookie}".encode()))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


def test_activity_is_noted_at_most_every_few_minutes() -> None:
    core_auth._last_noted.clear()
    with patch.object(core_auth, "asyncio") as fake_asyncio:
        loop = Mock()
        loop.create_task.return_value = Mock()
        fake_asyncio.get_running_loop.return_value = loop
        assert core_auth.note_activity("session", "h1", 1_000) is True
        assert core_auth.note_activity("session", "h1", 1_100) is False
        assert core_auth.note_activity("session", "h1", 1_000 + 300) is True
        assert loop.create_task.call_count == 2
    # the coroutines handed to the mocked loop were never started
    for call in loop.create_task.call_args_list:
        call.args[0].close()


def test_activity_outside_a_running_loop_is_skipped() -> None:
    core_auth._last_noted.clear()
    assert core_auth.note_activity("key", "h2", 5_000) is False


@pytest.mark.asyncio
async def test_activity_write_failure_is_swallowed() -> None:
    class Boom:
        async def __aenter__(self):
            raise RuntimeError("database down")

        async def __aexit__(self, *exc):
            return False

    with patch("src.database.session.SessionLocal", return_value=Boom()):
        await core_auth._write_activity("session", "h3", 1)


@pytest.mark.asyncio
async def test_list_sessions_marks_this_browser_and_puts_it_first() -> None:
    mine = SimpleNamespace(
        id=uuid4(),
        token_hash=hash_token("mine"),
        user_agent="Firefox",
        created_at=10,
        last_seen_at=20,
    )
    other = SimpleNamespace(
        id=uuid4(),
        token_hash=hash_token("other"),
        user_agent="Phone",
        created_at=5,
        last_seen_at=99,
    )
    db = AsyncMock()
    db.scalars.return_value = [other, mine]
    rows = await auth_routes.list_my_sessions(
        _request("mine"), user=SimpleNamespace(id=uuid4()), db=db
    )
    assert [r["current"] for r in rows] == [True, False]
    assert rows[0]["user_agent"] == "Firefox"
    assert all("token" not in key for r in rows for key in r)


@pytest.mark.asyncio
async def test_this_browser_cannot_be_signed_out_from_the_list() -> None:
    row = SimpleNamespace(id=uuid4(), token_hash=hash_token("mine"))
    db = AsyncMock()
    db.scalar.return_value = row
    with pytest.raises(HTTPException) as exc:
        await auth_routes.sign_out_session(
            row.id, _request("mine"), user=SimpleNamespace(id=uuid4()), db=db
        )
    assert exc.value.status_code == 400
    db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_signing_out_another_device_deletes_only_that_one() -> None:
    row = SimpleNamespace(id=uuid4(), token_hash=hash_token("other"))
    db = AsyncMock()
    db.scalar.return_value = row
    result = await auth_routes.sign_out_session(
        row.id, _request("mine"), user=SimpleNamespace(id=uuid4()), db=db
    )
    assert result == {"status": "signed_out"}
    db.delete.assert_awaited_once_with(row)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sign_out_others_keeps_this_browser() -> None:
    db = AsyncMock()
    db.execute.return_value = Mock(rowcount=2)
    result = await auth_routes.sign_out_other_sessions(
        _request("mine"), user=SimpleNamespace(id=uuid4()), db=db
    )
    assert result == {"signed_out": 2}
    statement = db.execute.await_args.args[0]
    assert hash_token("mine") in statement.compile().params.values()
