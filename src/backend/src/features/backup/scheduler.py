"""Scheduled automatic backups, an in-process asyncio loop, same pattern as
the trash sweep (src/features/trash/sweep.py): no new worker container, no
new dependency. Runs once at startup and then on a fixed interval, writing
one JSON snapshot per user in the same shape as the manual Export/Import
feature (src/api/routes/export_import.py), so a backup file can be fed
straight back through POST /api/import/library if it's ever needed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from sqlalchemy import select

from src.api.schemas.game import GameRead
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import SessionLocal

logger = logging.getLogger(__name__)

_BACKUP_ROOT = Path("/data/backups")
BACKUP_INTERVAL_SECONDS = 24 * 60 * 60
BACKUPS_TO_KEEP_PER_USER = 7


async def run_backup_for_user(user_id) -> Path | None:
    async with SessionLocal() as db:
        stmt = (
            select(Game)
            .where(Game.user_id == user_id, Game.deleted_at.is_(None))
            .order_by(Game.sort_title)
        )
        games = list((await db.execute(stmt)).scalars().all())
        if not games:
            return None

        payload = {
            "format_version": 1,
            "exported_at": int(time.time()),
            "game_count": len(games),
            "games": [GameRead.model_validate(g).model_dump(mode="json") for g in games],
        }

        user_dir = _BACKUP_ROOT / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        backup_path = user_dir / f"backup-{payload['exported_at']}.json"
        backup_path.write_text(json.dumps(payload))

        # keep only the most recent N, this is a rolling safety net, not a
        # long-term archive (that's what the manual Export button is for)
        existing = sorted(user_dir.glob("backup-*.json"), reverse=True)
        for stale in existing[BACKUPS_TO_KEEP_PER_USER:]:
            stale.unlink(missing_ok=True)

        return backup_path


async def run_all_backups() -> int:
    async with SessionLocal() as db:
        user_ids = [row[0] for row in (await db.execute(select(User.id))).all()]

    written = 0
    for user_id in user_ids:
        try:
            if await run_backup_for_user(user_id):
                written += 1
        except Exception:
            logger.exception("Backup failed for user %s", user_id)

    if written:
        logger.info("Automatic backup wrote %d user snapshot(s)", written)
    return written


async def run_backup_loop() -> None:
    while True:
        try:
            await run_all_backups()
        except Exception:
            logger.exception("Automatic backup loop failed")
        await asyncio.sleep(BACKUP_INTERVAL_SECONDS)
