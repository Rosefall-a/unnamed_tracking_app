"""Scheduled automatic backups, an in-process asyncio loop, same pattern as
the trash sweep (src/features/trash/sweep.py): no new worker container, no
new dependency. What a backup holds and how it is kept safe is in
snapshot.py.

The schedule is set by an admin in Settings > Admin > Backups and stored in
the job_settings row "auto_backup": whether it runs by itself, how often,
and (in options) how many backups to keep. A run is due when the
last one is older than the interval, so restarting the server does not add
an extra backup each time. After a failed run it is due again an hour later,
so one bad night does not leave a whole interval without a backup.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.anime import Anime
from src.database.models.game import Game
from src.database.models.job_setting import JobSetting
from src.database.models.movies import Movie
from src.database.models.tv_show import TVShow
from src.database.session import SessionLocal
from src.features.backup import snapshot

logger = logging.getLogger(__name__)

JOB_ID = "auto_backup"
DEFAULT_INTERVAL_MINUTES = 24 * 60
MIN_INTERVAL_MINUTES = 60
MAX_INTERVAL_MINUTES = 30 * 24 * 60
RETRY_AFTER_FAILURE_MINUTES = 60
DEFAULT_KEEP = 7
MAX_KEEP = 365
TICK_SECONDS = 60

_running = False


def is_running() -> bool:
    return _running


async def get_setting(db: AsyncSession) -> JobSetting:
    row = await db.get(JobSetting, JOB_ID)
    if row is None:
        row = JobSetting(
            job_id=JOB_ID,
            enabled=True,
            interval_minutes=DEFAULT_INTERVAL_MINUTES,
            options={"keep": DEFAULT_KEEP},
        )
        db.add(row)
        await db.flush()
    return row


def keep_count(row: JobSetting) -> int:
    try:
        return int((row.options or {}).get("keep", DEFAULT_KEEP))
    except (TypeError, ValueError):
        return DEFAULT_KEEP


def is_due(row: JobSetting, now: float) -> bool:
    if not row.enabled:
        return False
    if row.last_run_at is None:
        return True
    wait = row.interval_minutes
    if (row.last_result or {}).get("status") == "failed":
        wait = min(wait, RETRY_AFTER_FAILURE_MINUTES)
    return now - row.last_run_at >= wait * 60


async def _count_items() -> int:
    async with SessionLocal() as db:
        total = 0
        for model in (Game, Movie, TVShow, Anime):
            total += (
                await db.scalar(
                    select(func.count()).select_from(model).where(model.deleted_at.is_(None))
                )
            ) or 0
        return total


async def run_backup() -> dict[str, Any]:
    """One whole-database backup, then rotation. Never raises: the result
    says what happened and is shown in Settings > Admin > Backups."""
    global _running
    _running = True
    result: dict[str, Any] = {"status": "failed", "removed": 0, "held": None, "error": None}
    try:
        async with SessionLocal() as db:
            keep = keep_count(await get_setting(db))
            await db.commit()
        items = await _count_items()
        snapshot.clear_partials(snapshot.DATABASE_DIR)
        info = await asyncio.to_thread(snapshot.write_backup, snapshot.DATABASE_DIR, items)
        removed, held = await asyncio.to_thread(snapshot.rotate, snapshot.DATABASE_DIR, keep)
        result.update(status="written", name=info.name, size=info.size, removed=removed, held=held)
        if held:
            logger.warning("Backup rotation held: %s", held)
        logger.info("Automatic backup: %s", result)
    except Exception as exc:
        logger.exception("Automatic backup failed")
        result["error"] = str(exc)[:500]
    finally:
        try:
            async with SessionLocal() as db:
                row = await get_setting(db)
                row.last_run_at = int(time.time())
                row.last_result = result
                await db.commit()
        finally:
            _running = False
    return result


def start_now() -> bool:
    """Starts a run in the background. False when one is already running."""
    global _running
    if _running:
        return False
    # set before the task starts, so a second click in between is refused
    _running = True
    asyncio.get_running_loop().create_task(run_backup())
    return True


async def run_backup_loop() -> None:
    while True:
        try:
            async with SessionLocal() as db:
                due = is_due(await get_setting(db), time.time())
                await db.commit()
            if due and not _running:
                await run_backup()
        except Exception:
            logger.exception("Automatic backup loop failed; it will try again")
        await asyncio.sleep(TICK_SECONDS)
