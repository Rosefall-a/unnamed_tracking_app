"""Test accounts are named t_<hex> or ics_<hex> with an @example.test email. Each
test removes its own, but a run that is stopped or fails halfway leaves some
behind, and on the PC stack the tests share the real database. At the end of
a run, any such account made during that run is removed. Nothing older is
touched, and never an admin or an account with any other email.

Files go the same way: every folder under /data the app's code knows about is
pointed at a fresh temporary folder for each test, so a test can never leave
files in the real data folder (some used to, through modules that keep their
own copy of the path). A test that sets its own folder still does.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

_STARTED_AT = 0

_REMOVE_TEST_ACCOUNTS = text(
    r"""
    DELETE FROM users
    WHERE username ~ '^(t|ics)_[0-9a-f]{8,10}$'
      AND email LIKE '%@example.test'
      AND NOT is_admin
      AND created_at >= :since
    """
)


_DATA = Path("/data")


def _under_data(value: object) -> bool:
    return isinstance(value, Path) and (value == _DATA or _DATA in value.parents)


@pytest.fixture(autouse=True)
def _private_data_folder(tmp_path, monkeypatch):
    """Points every module-level path under /data (and tuples of them) at the
    same place under this test's own temporary folder."""
    root = tmp_path / "data"

    def moved(path: Path) -> Path:
        return root / path.relative_to(_DATA)

    for name, module in list(sys.modules.items()):
        if module is None or not name.startswith("src."):
            continue
        for attr, value in list(vars(module).items()):
            if _under_data(value):
                monkeypatch.setattr(module, attr, moved(value))
            elif (
                isinstance(value, tuple)
                and value
                and all(_under_data(item) for item in value)
            ):
                monkeypatch.setattr(module, attr, tuple(moved(item) for item in value))
    yield


def pytest_sessionstart(session: pytest.Session) -> None:
    global _STARTED_AT
    # a second early, so an account made in the same second still counts
    _STARTED_AT = int(time.time()) - 1


async def _remove_test_accounts(since: int) -> int:
    from src.core.config import settings

    # its own engine: the app's pool belongs to event loops the tests have closed
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(_REMOVE_TEST_ACCOUNTS, {"since": since})
            return result.rowcount or 0
    finally:
        await engine.dispose()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not _STARTED_AT:
        return
    try:
        removed = asyncio.run(_remove_test_accounts(_STARTED_AT))
    except Exception as exc:  # the run's own result matters more than this tidy-up
        print(f"\nCould not remove test accounts left by this run: {exc}")
        return
    if removed:
        print(f"\nRemoved {removed} test account(s) this run left behind.")
