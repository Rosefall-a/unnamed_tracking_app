from unittest.mock import AsyncMock, Mock

import pytest

from src.features.auth.cleanup import cleanup_expired_authentication_records


@pytest.mark.asyncio
async def test_cleanup_removes_only_records_that_cannot_be_used() -> None:
    db = AsyncMock()
    db.execute.side_effect = [
        Mock(rowcount=2),
        Mock(rowcount=3),
        Mock(rowcount=4),
        Mock(rowcount=5),
    ]

    counts = await cleanup_expired_authentication_records(db, now=1_000)

    assert counts == (2, 3, 4, 5)
    assert db.execute.await_count == 4
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_propagates_database_failures_for_startup_caller_to_handle() -> None:
    db = AsyncMock()
    db.execute.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        await cleanup_expired_authentication_records(db, now=1_000)

    db.commit.assert_not_awaited()
