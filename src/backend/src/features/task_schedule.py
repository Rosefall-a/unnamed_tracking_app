"""Tasks that run together, once a day at a set time.

Each task (and the backup) runs one of three ways, picked in Settings > Tasks:
off, on its own timer (every so many minutes, hours or days), or together with
the others. The ones set to run together start at the set time, one after
another, and the backup goes last so it holds what they just did. Nothing joins
by itself: every task starts on its own timer.

The time is the job_settings row "task_schedule": in options, the time
("03:00") and the time zone it is in ("Europe/London"), since the server runs on
UTC. `last_run_at` is when the last run together started. Whether a task runs
together is `options["together"]` on that task's own row. If the server was off
at the set time, the run happens when it is next up.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.job_setting import JobSetting
from src.database.session import SessionLocal
from src.features import jobs
from src.features.backup import scheduler as backups

logger = logging.getLogger(__name__)

SCHEDULE_ID = "task_schedule"
DEFAULT_TIME = "03:00"
# the order they run in: imports first, so the repair and refresh see new titles
ORDER = ("airing_check", "steam_import", "game_repair", "media_refresh", "sequel_check")
POLL_SECONDS = 5
# a task that has not finished by then is left running and the next one starts
MAX_WAIT_SECONDS = 6 * 60 * 60

_TIME = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_STATE = {"running": False}


def is_running() -> bool:
    """Whether a run together is going on now."""
    return _STATE["running"]


def valid_time(value: str) -> bool:
    """A time written like 03:00."""
    return bool(_TIME.match(value))


def zone(name: str) -> ZoneInfo:
    """The named time zone, or UTC when the name is not known."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def valid_zone(name: str) -> bool:
    """Whether the server knows this time zone."""
    try:
        ZoneInfo(name)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def together(row: JobSetting) -> bool:
    """Whether this task runs with the others at the set time."""
    return row.enabled and bool((row.options or {}).get("together"))


def set_together(row: JobSetting, value: bool) -> None:
    """Puts a task in or out of the run together."""
    row.options = {**(row.options or {}), "together": value}


async def get_schedule(db: AsyncSession) -> JobSetting:
    """The row holding the time, made with the default time the first time."""
    row = await db.get(JobSetting, SCHEDULE_ID)
    if row is None:
        row = JobSetting(
            job_id=SCHEDULE_ID,
            enabled=True,
            interval_minutes=24 * 60,
            options={"time": DEFAULT_TIME, "timezone": "UTC"},
        )
        db.add(row)
        await db.flush()
    return row


def arm(row: JobSetting) -> None:
    """The next run together is at the next set time, not straight away for a
    time that already passed today."""
    row.options = {**(row.options or {}), "armed_at": int(time.time())}


def _time_and_zone(row: JobSetting) -> tuple[int, int, ZoneInfo]:
    options = row.options or {}
    match = _TIME.match(str(options.get("time") or DEFAULT_TIME)) or _TIME.match(DEFAULT_TIME)
    assert match is not None
    return int(match.group(1)), int(match.group(2)), zone(str(options.get("timezone") or "UTC"))


def slot_before(row: JobSetting, now: float) -> int:
    """The latest set time at or before `now`, as a Unix time."""
    hour, minute, tz = _time_and_zone(row)
    local_now = datetime.fromtimestamp(now, tz)
    slot = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if slot > local_now:
        slot = (local_now - timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return int(slot.timestamp())


def next_slot(row: JobSetting, now: float) -> int:
    """The next set time after `now`, as a Unix time."""
    hour, minute, tz = _time_and_zone(row)
    local_now = datetime.fromtimestamp(now, tz)
    slot = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if slot <= local_now:
        slot = (local_now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return int(slot.timestamp())


def is_due(row: JobSetting, now: float) -> bool:
    """Whether the set time has passed since the last run (or since the time
    was last changed or a task joined)."""
    since = max(row.last_run_at or 0, int((row.options or {}).get("armed_at") or 0))
    return since < slot_before(row, now)


async def members(db: AsyncSession) -> list[str]:
    """The tasks set to run together, in the order they run, the backup last."""
    out = [job_id for job_id in ORDER if together(await jobs.get_setting(db, jobs.JOBS[job_id]))]
    if together(await backups.get_setting(db)):
        out.append(backups.JOB_ID)
    return out


async def describe(db: AsyncSession, row: JobSetting, now: float | None = None) -> dict[str, Any]:
    """The time, when the next run together is (none while no task is in it),
    and how the last one went."""
    now = time.time() if now is None else now
    options = row.options or {}
    joined = await members(db)
    return {
        "time": str(options.get("time") or DEFAULT_TIME),
        "timezone": str(options.get("timezone") or "UTC"),
        "members": joined,
        "last_run_at": row.last_run_at,
        "last_result": row.last_result or {},
        "next_run_at": next_slot(row, now) if joined else None,
        "running": _STATE["running"],
    }


async def _wait_for(spec: jobs.JobSpec) -> bool:
    waited = 0
    while spec.is_running() and waited < MAX_WAIT_SECONDS:
        await asyncio.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
    return not spec.is_running()


async def run_together() -> dict[str, Any]:
    """Runs every task set to run together, one after another, then the backup."""
    _STATE["running"] = True
    result: dict[str, Any] = {"ran": [], "unfinished": []}
    try:
        async with SessionLocal() as db:
            row = await get_schedule(db)
            # noted first, so a restart halfway through does not start it again
            row.last_run_at = int(time.time())
            row.last_result = {"status": "running"}
            joined = await members(db)
            await db.commit()
        for job_id in joined:
            if job_id == backups.JOB_ID:
                continue
            spec = jobs.JOBS[job_id]
            # one started by hand a moment ago is waited for, not started twice
            if not spec.is_running():
                logger.info("Tasks run together: starting %s", job_id)
                spec.start("needed")
                # it starts in the background; give it a moment to say so
                await asyncio.sleep(1)
            finished = await _wait_for(spec)
            result["ran" if finished else "unfinished"].append(job_id)
        if backups.JOB_ID in joined:
            if not backups.is_running():
                logger.info("Tasks run together: starting the backup")
                await backups.run_backup()
            result["ran"].append(backups.JOB_ID)
        result["status"] = "done"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("Running the tasks together failed")
        result.update(status="failed", error=str(exc)[:500])
    finally:
        try:
            async with SessionLocal() as db:
                row = await get_schedule(db)
                row.last_result = {**result, "finished_at": int(time.time())}
                await db.commit()
        finally:
            _STATE["running"] = False
    return result


def start_now() -> bool:
    """Starts the run together in the background. False when one is running."""
    if _STATE["running"]:
        return False
    _STATE["running"] = True
    asyncio.get_running_loop().create_task(run_together())
    return True
