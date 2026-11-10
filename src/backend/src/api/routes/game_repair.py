"""Settings > Administration > Repair: see what libraries are missing and fill it
in without a reimport. Looking changes nothing, and a run only ever adds (see
features/metadata/games/repair.py). One run at a time, tracked in memory, so a
server restart ends a run; running again carries on where it stopped."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_admin
from src.database.models.user import User
from src.database.session import SessionLocal, get_db
from src.features import jobs
from src.features.legacy_files import restore_old_files, scan_old_files
from src.features.offline_pictures import count_missing, save_missing
from src.features.metadata.games.repair import (
    games_with_problem,
    repair_all_games,
    replace_all_poor_covers,
    replace_poor_covers,
    repair_single_game,
    repair_user_games,
    scan_libraries,
)

router = APIRouter(
    prefix="/api/settings/repair", tags=["settings"], dependencies=[Depends(get_current_admin)]
)
logger = logging.getLogger(__name__)


class RepairRequest(BaseModel):
    # nobody named means everyone
    user_id: UUID | None = None
    # also games checked in the last 30 days
    force: bool = False
    # instead of filling blanks, look for covers that are only Steam's poor ones
    covers: bool = False
    # instead of filling blanks, save a local copy of every picture still only online
    pictures: bool = False


@dataclass
class RepairRun:
    running: bool = False
    who: str = ""
    done: int = 0
    total: int = 0
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    finished_at: int | None = None


_run = RepairRun()
_tasks: set[asyncio.Task[None]] = set()


def _progress(who: str, done: int, total: int) -> None:
    _run.who, _run.done, _run.total = who, done, total


async def _go(
    user_id: UUID | None, username: str | None, force: bool, covers: bool, pictures: bool = False
) -> None:
    try:
        if pictures and user_id is not None:
            _run.result = await save_missing(
                user_id, lambda done, total: _progress(username or "", done, total)
            )
            return
        if covers and user_id is not None:
            result = asdict(
                await replace_poor_covers(
                    user_id, lambda done, total: _progress(username or "", done, total)
                )
            )
        elif covers:
            result = await replace_all_poor_covers(_progress)
        elif user_id is not None:
            result = asdict(
                await repair_user_games(
                    user_id, lambda done, total: _progress(username or "", done, total), force
                )
            )
        else:
            result = await repair_all_games(_progress, force)
        _run.result = result
        await jobs.record_run("game_repair", result)
    except Exception as exc:  # reported on the screen instead of vanishing
        logger.exception("The repair run failed")
        _run.error = str(exc) or "The repair failed."
    finally:
        _run.running = False
        _run.finished_at = int(time.time())


@router.get("/scan")
async def scan() -> list[dict[str, Any]]:
    people = await scan_libraries()
    for person in people:
        # pictures a page would have to fetch from another site, so not viewable offline
        person["offline_missing"] = await count_missing(UUID(str(person["user_id"])))
    return people


@router.get("/games")
async def list_games(user_id: UUID, problem: str) -> list[dict[str, Any]]:
    return await games_with_problem(user_id, problem)


@router.get("/status")
async def run_status() -> dict[str, Any]:
    return asdict(_run)


@router.post("/run")
async def start_run(body: RepairRequest) -> dict[str, Any]:
    if _run.running:
        return asdict(_run)
    if jobs.JOBS["game_repair"].is_running():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The scheduled repair is running. Try again when it has finished.",
        )
    username = None
    if body.user_id is not None:
        async with SessionLocal() as db:
            username = await db.scalar(select(User.username).where(User.id == body.user_id))
        if username is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such person.")
    _run.running, _run.who, _run.done, _run.total = True, username or "everyone", 0, 0
    if body.pictures and body.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Pick whose pictures to save."
        )
    _run.result, _run.error, _run.finished_at = {}, None, None
    task = asyncio.get_running_loop().create_task(
        _go(body.user_id, username, body.force, body.covers, body.pictures)
    )
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return asdict(_run)


@router.get("/old-files")
async def old_files(user_id: UUID, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await scan_old_files(db, user_id)
    await db.commit()
    return result


@router.post("/old-files")
async def bring_back_old_files(
    user_id: UUID, db: AsyncSession = Depends(get_db)
) -> dict[str, int]:
    return await restore_old_files(db, user_id)


@router.post("/games/{game_id}")
async def fix_one_game(game_id: UUID) -> dict[str, Any]:
    result = await repair_single_game(game_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such game.")
    return asdict(result)
