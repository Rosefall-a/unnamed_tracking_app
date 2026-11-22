"""Tasks set to run together start once a day at a set time, in the person's
own time zone: when that is due, that joining never starts a run straight away,
that only the chosen tasks run, one after another, with the backup last, and
that the API keeps each task's choice."""

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest

from src.core.auth import get_current_admin
from src.database.models.job_setting import JobSetting
from src.database.models.user import User
from src.features import jobs, task_schedule
from src.features.backup import scheduler as backups
from src.main import app


def _row(at="03:00", tz="Europe/London", last=None, armed=None) -> JobSetting:
    options = {"time": at, "timezone": tz}
    if armed is not None:
        options["armed_at"] = armed
    return JobSetting(job_id="task_schedule", enabled=True, interval_minutes=1440, last_run_at=last, options=options)


def _at(text: str, tz: str = "Europe/London") -> int:
    return int(datetime.fromisoformat(text).replace(tzinfo=ZoneInfo(tz)).timestamp())


def _task(job_id: str, enabled: bool, together: bool) -> JobSetting:
    return JobSetting(job_id=job_id, enabled=enabled, interval_minutes=1440, options={"together": together})


def test_the_set_time_is_in_the_persons_own_time_zone() -> None:
    # 03:00 in London during summer time is 02:00 UTC
    row = _row(at="03:00", tz="Europe/London")
    assert task_schedule.next_slot(row, _at("2026-07-01T01:00")) == _at("2026-07-01T03:00")
    assert task_schedule.next_slot(row, _at("2026-07-01T03:00")) == _at("2026-07-02T03:00")
    assert task_schedule.slot_before(row, _at("2026-07-01T02:59")) == _at("2026-06-30T03:00")


def test_due_once_the_time_passes_and_not_again_that_day() -> None:
    row = _row(armed=_at("2026-11-10T12:00"))
    assert not task_schedule.is_due(row, _at("2026-11-11T02:59"))
    assert task_schedule.is_due(row, _at("2026-11-11T03:00"))
    row.last_run_at = _at("2026-11-11T03:00")
    assert not task_schedule.is_due(row, _at("2026-11-11T23:00"))
    assert task_schedule.is_due(row, _at("2026-11-12T03:01"))


def test_joining_after_todays_time_waits_for_tomorrow() -> None:
    row = _row(armed=_at("2026-11-11T10:00"))
    assert not task_schedule.is_due(row, _at("2026-11-11T10:01"))
    assert task_schedule.is_due(row, _at("2026-11-12T03:00"))


def test_a_run_missed_while_the_server_was_off_happens_when_it_is_back() -> None:
    row = _row(armed=_at("2026-11-09T12:00"), last=_at("2026-11-10T03:00"))
    assert task_schedule.is_due(row, _at("2026-11-11T09:30"))


def test_a_task_that_is_off_never_runs_together() -> None:
    assert task_schedule.together(_task("x", True, True))
    assert not task_schedule.together(_task("x", False, True))
    assert not task_schedule.together(_task("x", True, False))
    assert not task_schedule.together(JobSetting(job_id="x", enabled=True, interval_minutes=1, options=None))


class _FakeTask:
    def __init__(self, name: str, log: list[str]) -> None:
        self.name, self.log, self.left = name, log, 0

    def start(self, _mode: str) -> dict:
        self.log.append(f"start {self.name}")
        self.left = 2
        return {}

    def is_running(self) -> bool:
        if self.left:
            self.left -= 1
            if not self.left:
                self.log.append(f"end {self.name}")
        return bool(self.left)


async def test_only_the_chosen_tasks_run_one_after_another_and_the_backup_last(monkeypatch) -> None:
    log: list[str] = []
    fakes = {job_id: _FakeTask(job_id, log) for job_id in task_schedule.ORDER}
    monkeypatch.setattr(
        jobs,
        "JOBS",
        {
            job_id: jobs.JobSpec(job_id, job_id, "", 5, 1440, 1440, True, fake.start, fake.is_running, lambda r: "")
            for job_id, fake in fakes.items()
        },
    )
    monkeypatch.setattr(task_schedule, "POLL_SECONDS", 0)

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(task_schedule.asyncio, "sleep", no_wait)
    # the airing check keeps its own timer, the repair is off
    choices = {
        "airing_check": _task("airing_check", True, False),
        "steam_import": _task("steam_import", True, True),
        "game_repair": _task("game_repair", False, True),
        "media_refresh": _task("media_refresh", True, True),
        "sequel_check": _task("sequel_check", True, True),
    }

    async def setting(_db, spec):
        return choices[spec.id]

    monkeypatch.setattr(jobs, "get_setting", setting)

    async def fake_backup():
        log.append("backup")
        return {}

    monkeypatch.setattr(backups, "run_backup", fake_backup)

    async def backup_setting(_db):
        return _task("auto_backup", True, True)

    monkeypatch.setattr(backups, "get_setting", backup_setting)
    schedule = _row()

    async def the_schedule(_db):
        return schedule

    monkeypatch.setattr(task_schedule, "get_schedule", the_schedule)

    result = await task_schedule.run_together()

    assert log == [
        "start steam_import",
        "end steam_import",
        "start media_refresh",
        "end media_refresh",
        "start sequel_check",
        "end sequel_check",
        "backup",
    ]
    assert result["status"] == "done"
    assert schedule.last_result["status"] == "done"
    assert not task_schedule.is_running()


@pytest.mark.parametrize("value", ["3:00", "24:00", "03:60", "noon", ""])
def test_only_real_times_are_accepted(value: str) -> None:
    assert not task_schedule.valid_time(value)


async def test_the_api_keeps_each_tasks_choice_and_puts_it_back(monkeypatch) -> None:
    """A real round trip, on the deployment's own rows, left as they were."""
    from src.database.session import SessionLocal

    async with SessionLocal() as db:
        spec = jobs.JOBS["sequel_check"]
        row = await jobs.get_setting(db, spec)
        before = (row.enabled, row.interval_minutes, dict(row.options or {}) if row.options else None)
        existing = await db.get(JobSetting, task_schedule.SCHEDULE_ID)
        had_schedule = existing is not None
        schedule_before = (
            (dict(existing.options or {}), existing.last_run_at, existing.last_result)
            if existing is not None
            else None
        )
        await db.commit()
    app.dependency_overrides[get_current_admin] = lambda: User(id=uuid.uuid4(), is_admin=True)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            joined = await client.put("/api/settings/jobs/sequel_check", json={"enabled": True, "together": True})
            assert joined.status_code == 200, joined.text
            assert joined.json()["together"] is True
            schedule = (await client.get("/api/settings/jobs/schedule")).json()
            assert "sequel_check" in schedule["members"]
            assert schedule["next_run_at"]
            left = await client.put("/api/settings/jobs/sequel_check", json={"together": False})
            assert left.json()["together"] is False
            bad = await client.put("/api/settings/jobs/schedule", json={"time": "25:00"})
            assert bad.status_code == 400
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
        async with SessionLocal() as db:
            row = await jobs.get_setting(db, spec)
            row.enabled, row.interval_minutes, row.options = before
            made = await db.get(JobSetting, task_schedule.SCHEDULE_ID)
            if made is not None and not had_schedule:
                await db.delete(made)
            elif made is not None and schedule_before is not None:
                made.options, made.last_run_at, made.last_result = schedule_before
            await db.commit()
