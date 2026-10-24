"""A library import that runs on the server from start to finish.

The app used to drive an import itself: one request to save the games, then
batches of requests for achievements, the wishlist and each new game's store
details and artwork. Closing or reloading the page stopped those batches, which
left most new games with only a name. Now the app asks for an import once and
the server runs every step (the same functions the step routes use, a few games
at a time) while the app only reads the progress.

One import per person at a time. The progress lives in memory, so a server
restart ends a running import; the next import picks up the games it did not
reach (see helpers/steam_bare_games.py)."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.api.routes import epic_import, library_sync, steam_import_steps
from src.core.auth import get_current_user
from src.database.models.user import User
from src.database.session import SessionLocal

router = APIRouter(
    prefix="/api/library-sync/import",
    tags=["library-sync"],
    dependencies=[Depends(get_current_user)],
)
logger = logging.getLogger(__name__)
_CURRENT_USER = Depends(get_current_user)

Provider = Literal["steam", "psn", "retroachievements", "epic"]

# the batch sizes the app used when it drove the steps itself
_ACHIEVEMENT_BATCH = 10
_ENRICH_BATCH = 5
# Epic adds a few games per step; a bound stops a server that keeps saying
# "carry on" (or the same place twice) from looping for ever
_EPIC_MAX_STEPS = 1000


@dataclass
class ImportJob:  # pylint: disable=too-many-instance-attributes
    """What one import is doing, as the app shows it."""

    provider: str
    running: bool = True
    step: str = "Starting"
    done: int = 0
    total: int = 0
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: int = field(default_factory=lambda: int(time.time()))
    finished_at: int | None = None


_jobs: dict[UUID, ImportJob] = {}
_tasks: set[asyncio.Task[None]] = set()


async def _as_user(user_id: UUID, step: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
    """Run one import step the way its route would, in a session of its own."""
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        if user is None:
            raise RuntimeError("The account no longer exists.")
        return await step(*args, db=db, current_user=user, **kwargs)


def _progress(job: ImportJob, step: str, done: int, total: int) -> None:
    job.step, job.done, job.total = step, done, total


async def _import_steam(user_id: UUID, job: ImportJob) -> dict[str, Any]:
    _progress(job, "Reading your Steam library", 0, 1)
    result: dict[str, Any] = await _as_user(
        user_id, library_sync.sync_steam_library, achievements="later"
    )

    achievement_ids = list(result.get("achievement_game_ids") or [])
    settle = set(result.get("status_game_ids") or [])
    unavailable = list(result.get("achievements_unavailable") or [])
    achievements_failed = 0
    for start in range(0, len(achievement_ids), _ACHIEVEMENT_BATCH):
        _progress(job, "Reading achievements", start, len(achievement_ids))
        chunk = [UUID(i) for i in achievement_ids[start : start + _ACHIEVEMENT_BATCH]]
        try:
            batch = await _as_user(
                user_id,
                steam_import_steps.import_achievements,
                steam_import_steps.AchievementsRequest(
                    game_ids=chunk, status_game_ids=[i for i in chunk if str(i) in settle]
                ),
            )
        except Exception:  # the games are saved; their achievements come in on the next import
            logger.exception("Steam achievements batch failed")
            achievements_failed += len(chunk)
            continue
        result["achievements_synced"] += batch["achievements_synced"]
        unavailable.extend(batch["achievements_unavailable"])
    result["achievements_unavailable"] = unavailable
    result["achievements_failed"] = achievements_failed

    enrich_ids = list(result.get("enrich_game_ids") or [])
    # the wishlist is an extra: if Steam won't give it, the owned games still
    # need their store details and artwork
    _progress(job, "Reading your wishlist", 0, 1)
    try:
        wishlist = await _as_user(user_id, steam_import_steps.import_wishlist)
        result["wishlist_added"] = wishlist["added"]
        enrich_ids.extend(i for i in wishlist["game_ids"] if i not in enrich_ids)
    except Exception:
        logger.exception("Steam wishlist import failed")
        result["wishlist_added"] = 0

    enrich_failed = 0
    for start in range(0, len(enrich_ids), _ENRICH_BATCH):
        _progress(job, "Adding artwork and details", start, len(enrich_ids))
        chunk = [UUID(i) for i in enrich_ids[start : start + _ENRICH_BATCH]]
        try:
            batch = await _as_user(
                user_id, steam_import_steps.enrich_games, steam_import_steps.EnrichRequest(game_ids=chunk)
            )
            enrich_failed += batch["failed"]
        except Exception:  # left bare; the next import tries these again
            logger.exception("Steam enrich batch failed")
            enrich_failed += len(chunk)
    result["enrich_failed"] = enrich_failed
    return result


async def _import_epic(user_id: UUID, job: ImportJob) -> dict[str, Any]:
    result: dict[str, Any] = {"games_added": 0, "games_updated": 0, "achievements_synced": 0, "games": []}
    after: str | None = None
    total: int | None = None
    _progress(job, "Reading your Epic library", 0, 1)
    for step in range(_EPIC_MAX_STEPS):
        batch = await _as_user(user_id, epic_import.sync_epic_library, after=after)
        if step == 0:
            # later steps also count the games the earlier ones just added
            result["games_updated"] = batch["games_updated"]
        result["games_added"] += batch["games_added"]
        result["games"].extend(batch["games"])
        if not batch["next"]:
            return result
        if batch["next"] == after:
            raise RuntimeError("Epic import stopped: the server did not move on.")
        total = total if total is not None else batch["pending"]
        _progress(job, "Adding games", total - batch["remaining"], total)
        after = batch["next"]
    raise RuntimeError("Epic import stopped: it never finished.")


async def _import_single(user_id: UUID, job: ImportJob, provider: Provider) -> dict[str, Any]:
    step = (
        library_sync.sync_psn_library
        if provider == "psn"
        else library_sync.sync_retroachievements_library
    )
    _progress(job, "Reading your library", 0, 1)
    result: dict[str, Any] = await _as_user(user_id, step)
    return result


async def _run(user_id: UUID, provider: Provider, job: ImportJob) -> None:
    try:
        if provider == "steam":
            job.result = await _import_steam(user_id, job)
        elif provider == "epic":
            job.result = await _import_epic(user_id, job)
        else:
            job.result = await _import_single(user_id, job, provider)
        job.step = "Done"
    except HTTPException as exc:
        job.error = str(exc.detail)
    except Exception as exc:  # reported on the screen instead of vanishing
        logger.exception("%s library import failed", provider)
        job.error = str(exc) or "The import failed."
    finally:
        job.running = False
        job.finished_at = int(time.time())


@router.post("/{provider}")
async def start_import(
    provider: Provider, current_user: User = _CURRENT_USER
) -> dict[str, Any]:
    """Start an import on the server and return its progress at once. If one is
    already running for this person, return that one instead of starting two."""
    running = _jobs.get(current_user.id)
    if running and running.running:
        return asdict(running)
    job = ImportJob(provider=provider)
    _jobs[current_user.id] = job
    task = asyncio.get_running_loop().create_task(_run(current_user.id, provider, job))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return asdict(job)


@router.get("/status")
async def import_status(current_user: User = _CURRENT_USER) -> dict[str, Any] | None:
    """This person's running or most recent import, or null if none since the
    server started."""
    job = _jobs.get(current_user.id)
    return asdict(job) if job else None
