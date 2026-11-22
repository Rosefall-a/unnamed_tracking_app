"""The Tasks screen's cleanup jobs: list them, change a schedule, run one now."""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_admin
from src.database.session import get_db
from src.features import task_schedule
from src.features.jobs import JOBS, JobSpec, describe, get_setting

router = APIRouter(
    prefix="/api/settings/jobs", tags=["settings"], dependencies=[Depends(get_current_admin)]
)


class ScheduleUpdate(BaseModel):
    """The time the tasks set to run together start."""

    # "03:00", in the time zone below
    time: str | None = None
    # the browser's own zone, e.g. "Europe/London"
    timezone: str | None = None


class JobUpdate(BaseModel):
    """A change to one task's schedule."""

    enabled: bool | None = None
    interval_minutes: int | None = None
    # runs with the others at the set time instead of its own timer
    together: bool | None = None


def _spec(job_id: str) -> JobSpec:
    spec = JOBS.get(job_id)
    if spec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such job.")
    return spec


async def _describe(db: AsyncSession, spec: JobSpec) -> dict[str, Any]:
    row = await get_setting(db, spec)
    return {**await describe(db, spec), "together": task_schedule.together(row)}


@router.get("")
async def list_jobs(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    """Every task, how it is scheduled, and how its last run went."""
    out = [await _describe(db, spec) for spec in JOBS.values()]
    await db.commit()
    return out


@router.get("/schedule")
async def get_task_schedule(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """The time the tasks set to run together start, and which tasks those are."""
    row = await task_schedule.get_schedule(db)
    out = await task_schedule.describe(db, row)
    await db.commit()
    return out


@router.put("/schedule")
async def update_task_schedule(
    payload: ScheduleUpdate, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Changes the time (in the browser's time zone)."""
    row = await task_schedule.get_schedule(db)
    options = dict(row.options or {})
    if payload.time is not None:
        if not task_schedule.valid_time(payload.time):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a time like 03:00.")
        options["time"] = payload.time
    if payload.timezone is not None:
        if not task_schedule.valid_zone(payload.timezone):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown time zone.")
        options["timezone"] = payload.timezone
    if options != (row.options or {}):
        row.options = options
        task_schedule.arm(row)
    out = await task_schedule.describe(db, row)
    await db.commit()
    return out


@router.post("/schedule/run")
async def run_task_schedule_now() -> dict[str, Any]:
    """Runs the tasks set to run together now, in the background."""
    return {"started": task_schedule.start_now(), "running": True}


@router.put("/{job_id}")
async def update_job(
    job_id: str, payload: JobUpdate, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Turns a task off, puts it on its own timer, or has it run with the others."""
    spec = _spec(job_id)
    row = await get_setting(db, spec)
    if payload.interval_minutes is not None:
        if not spec.min_interval_minutes <= payload.interval_minutes <= spec.max_interval_minutes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Interval must be between {spec.min_interval_minutes} and {spec.max_interval_minutes} minutes."
                ),
            )
        row.interval_minutes = payload.interval_minutes
    if payload.enabled is not None:
        row.enabled = payload.enabled
    if payload.together is not None:
        joining = payload.together and not task_schedule.together(row)
        task_schedule.set_together(row, payload.together)
        if joining:
            task_schedule.arm(await task_schedule.get_schedule(db))
    out = await _describe(db, spec)
    await db.commit()
    return out


@router.post("/{job_id}/run")
async def run_job(
    job_id: str,
    mode: str | None = Query(default=None, pattern="^(needed|all)$"),
) -> dict[str, Any]:
    """Starts a run now, in the background, the way that job is meant to be run
    by hand unless a mode is given. If one is already running, its progress is
    returned instead."""
    spec = _spec(job_id)
    return spec.start(mode or spec.manual_mode)
