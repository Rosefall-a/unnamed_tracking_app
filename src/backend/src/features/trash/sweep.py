"""Background sweep that permanently purges soft-deleted archives/versions
older than the retention window. Runs once at startup and then on a fixed
interval (see main.py) — in-process, no new container, matching how world
map renders already run as a plain asyncio background task rather than a
separate worker.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database.models.game import Game
from src.database.models.game_archive import GameArchive, GameArchiveVersion
from src.database.models.game_checklist_item import GameChecklistItem
from src.database.models.game_file_item import GameFileItem
from src.database.models.game_profile import GameProfile
from src.database.models.inbox_item import InboxItem
from src.database.models.media_item import MediaItem
from src.database.session import SessionLocal
from src.features.trash.archive_trash import purge_archive_trash, trash_files_dir
from src.features.trash.game_trash import purge_game_trash
from src.features.trash.inbox_trash import purge_inbox_file
from src.features.trash.media_trash import purge_media_file

logger = logging.getLogger(__name__)

_DATA_ROOT = Path("/data/games")
_USER_DATA_ROOT = Path("/data/user")
RETENTION_SECONDS = 7 * 24 * 60 * 60
SWEEP_INTERVAL_SECONDS = 6 * 60 * 60


async def purge_expired_trash() -> dict[str, int]:
    cutoff = int(time.time()) - RETENTION_SECONDS
    purged_archives = 0
    purged_versions = 0

    async with SessionLocal() as db:
        result = await db.execute(
            select(GameArchive)
            .options(selectinload(GameArchive.game), selectinload(GameArchive.versions))
            .where(GameArchive.deleted_at.is_not(None), GameArchive.deleted_at < cutoff)
        )
        for archive in result.scalars().all():
            if archive.game and archive.game.folder_location:
                purge_archive_trash(
                    _DATA_ROOT / archive.game.folder_location, archive.kind, archive.id
                )
            await db.delete(archive)  # cascades to remaining versions
            purged_archives += 1
        await db.commit()

        result = await db.execute(
            select(GameArchiveVersion)
            .options(selectinload(GameArchiveVersion.archive).selectinload(GameArchive.game))
            .where(
                GameArchiveVersion.deleted_at.is_not(None), GameArchiveVersion.deleted_at < cutoff
            )
        )
        for version in result.scalars().all():
            archive = version.archive
            if (
                archive
                and archive.deleted_at is None
                and archive.game
                and archive.game.folder_location
            ):
                trashed_file = (
                    trash_files_dir(
                        _DATA_ROOT / archive.game.folder_location, archive.kind, archive.id
                    )
                    / version.filename
                )
                trashed_file.unlink(missing_ok=True)
            await db.delete(version)
            purged_versions += 1
        await db.commit()

        result = await db.execute(
            select(InboxItem).where(
                InboxItem.deleted_at.is_not(None), InboxItem.deleted_at < cutoff
            )
        )
        purged_inbox_items = 0
        for item in result.scalars().all():
            inbox_dir = _USER_DATA_ROOT / str(item.user_id) / "inbox"
            purge_inbox_file(item.filename, inbox_dir, item.kind)
            await db.delete(item)
            purged_inbox_items += 1
        await db.commit()

        # media items before games: a media item whose game was ALSO trashed
        # still resolves its file path fine here (the game's own folder
        # move hasn't happened for anything still under retention), and
        # purging it now means one less row for the game's own cascade to
        # touch later
        result = await db.execute(
            select(MediaItem)
            .options(selectinload(MediaItem.game))
            .where(MediaItem.deleted_at.is_not(None), MediaItem.deleted_at < cutoff)
        )
        purged_media_items = 0
        for item in result.scalars().all():
            if item.game and item.game.folder_location:
                game_dir = _DATA_ROOT / item.game.folder_location
                purge_media_file(item.filename, game_dir, item.kind)
            await db.delete(item)
            purged_media_items += 1
        await db.commit()

        result = await db.execute(
            select(GameFileItem).where(
                GameFileItem.deleted_at.is_not(None), GameFileItem.deleted_at < cutoff
            )
        )
        purged_file_items = 0
        for item in result.scalars().all():
            # no ORM relationship on GameFileItem (plain game_id FK only) —
            # a direct lookup is simpler than adding one just for this
            game = await db.get(Game, item.game_id)
            if game and game.folder_location:
                game_dir = _DATA_ROOT / game.folder_location
                purge_media_file(item.filename, game_dir, item.kind)
            await db.delete(item)
            purged_file_items += 1
        await db.commit()

        # profiles and checklist items are DB-only (no files to move), so
        # purging one is just deleting the row once past retention
        result = await db.execute(
            select(GameProfile).where(
                GameProfile.deleted_at.is_not(None), GameProfile.deleted_at < cutoff
            )
        )
        purged_profiles = 0
        for profile in result.scalars().all():
            await db.delete(profile)
            purged_profiles += 1
        await db.commit()

        result = await db.execute(
            select(GameChecklistItem).where(
                GameChecklistItem.deleted_at.is_not(None), GameChecklistItem.deleted_at < cutoff
            )
        )
        purged_checklist_items = 0
        for item in result.scalars().all():
            await db.delete(item)
            purged_checklist_items += 1
        await db.commit()

        # games last — hard-deleting the row cascades to any remaining
        # archives/versions/media/achievements/notes still attached, and
        # purge_game_trash removes the whole folder tree (including any
        # nested archive/media trash subfolders that hadn't hit their own
        # retention yet) in one shot
        result = await db.execute(
            select(Game).where(Game.deleted_at.is_not(None), Game.deleted_at < cutoff)
        )
        purged_games = 0
        for game in result.scalars().all():
            purge_game_trash(_DATA_ROOT, game.id)
            await db.delete(game)
            purged_games += 1
        await db.commit()

    if (
        purged_archives
        or purged_versions
        or purged_inbox_items
        or purged_media_items
        or purged_file_items
        or purged_profiles
        or purged_checklist_items
        or purged_games
    ):
        logger.info(
            "Trash sweep purged %d game(s), %d archive(s), %d version(s), %d media item(s), "
            "%d file item(s), %d inbox item(s), %d profile(s), %d checklist item(s)",
            purged_games,
            purged_archives,
            purged_versions,
            purged_media_items,
            purged_file_items,
            purged_inbox_items,
            purged_profiles,
            purged_checklist_items,
        )
    return {
        "purged_games": purged_games,
        "purged_archives": purged_archives,
        "purged_versions": purged_versions,
        "purged_media_items": purged_media_items,
        "purged_file_items": purged_file_items,
        "purged_inbox_items": purged_inbox_items,
        "purged_profiles": purged_profiles,
        "purged_checklist_items": purged_checklist_items,
    }


async def run_sweep_loop() -> None:
    while True:
        try:
            await purge_expired_trash()
        except Exception:
            logger.exception("Trash sweep failed")
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
