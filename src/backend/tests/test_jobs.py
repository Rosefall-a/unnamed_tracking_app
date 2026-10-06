"""Built-in job execution keeps one worker active and recovers after failures."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.features import jobs


@pytest.mark.parametrize("fails", [False, True])
async def test_airing_job_does_not_overlap_and_can_restart_after_completion(monkeypatch, fails):
    entered = asyncio.Event()
    release = asyncio.Event()

    async def check(*, force):
        assert force is True
        entered.set()
        await release.wait()
        if fails:
            raise RuntimeError("provider unavailable")
        return {"checked": 3}

    check_mock = AsyncMock(side_effect=check)
    record_mock = AsyncMock()
    monkeypatch.setattr(jobs, "check_airing_episodes", check_mock)
    monkeypatch.setattr(jobs, "record_run", record_mock)
    spec = jobs.JOBS["airing_check"]
    assert not spec.is_running()
    tasks = asyncio.all_tasks()
    assert spec.start("all") == {"running": True}
    task = next(iter(asyncio.all_tasks() - tasks))
    await entered.wait()
    spec.start("all")
    assert spec.is_running()
    assert check_mock.await_count == 1
    release.set()
    await task
    assert not spec.is_running()
    if fails:
        record_mock.assert_not_awaited()
    else:
        record_mock.assert_awaited_once_with("airing_check", {"checked": 3})

    tasks = asyncio.all_tasks()
    spec.start("all")
    await next(iter(asyncio.all_tasks() - tasks))
    assert check_mock.await_count == 2
    assert not spec.is_running()
