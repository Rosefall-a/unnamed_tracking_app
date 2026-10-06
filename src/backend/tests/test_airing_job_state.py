"""Airing jobs report their state and release it after success or failure."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.features import jobs


@pytest.mark.parametrize("fails", [False, True])
async def test_airing_job_reports_state_and_prevents_duplicate_runs(monkeypatch, fails):
    started = asyncio.Event()
    release = asyncio.Event()

    async def check_airing(*, force):
        assert force is True
        started.set()
        await release.wait()
        if fails:
            raise RuntimeError("Provider unavailable")
        return {"checked": 1}

    check = AsyncMock(side_effect=check_airing)
    record = AsyncMock()
    monkeypatch.setattr(jobs, "check_airing_episodes", check)
    monkeypatch.setattr(jobs, "record_run", record)
    job = jobs.JOBS["airing_check"]
    assert job.is_running() is False

    previous_tasks = asyncio.all_tasks()
    assert job.start("all") == {"running": True}
    running_tasks = asyncio.all_tasks() - previous_tasks
    try:
        await asyncio.wait_for(started.wait(), timeout=2)
        assert job.is_running() is True
        assert job.start("all") == {"running": True}
        check.assert_awaited_once_with(force=True)
    finally:
        release.set()
        await asyncio.gather(*running_tasks)

    assert job.is_running() is False
    if fails:
        record.assert_not_awaited()
    else:
        record.assert_awaited_once_with("airing_check", {"checked": 1})
