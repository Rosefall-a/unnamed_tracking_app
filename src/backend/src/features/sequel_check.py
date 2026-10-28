"""Looks for newly listed seasons of anime you have finished, without anyone opening
the Related tab.

The notice itself (`record_sequel_announcements`) compares a title's franchise as it
was last stored with the franchise AniList lists now. Until now the only thing that
fetched a franchise was opening a title's Related tab with a cache over three days old,
so a season announced while you were not looking was never noticed. This is the
scheduled version of that fetch.

A franchise is many titles (Dr. Stone is eight), all with the same chain, so one fetch
covers the rest: titles whose AniList id is already in a chain fetched this run are
skipped. Each fetch is several paced AniList requests, so a run handles a few
franchises, the longest-unchecked first, and the next run carries on."""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import or_, select

from src.core.preferences import load_preferences
from src.database.models.anime import Anime, AnimeStatus
from src.database.models.user import User
from src.database.session import SessionLocal

logger = logging.getLogger(__name__)

# how long a stored franchise is trusted before the check asks AniList again
RECHECK_AFTER_SECONDS = 24 * 60 * 60
# franchises fetched per run: each costs a dozen or more paced AniList requests
MAX_FRANCHISES_PER_RUN = 6


async def check_sequels(force: bool = False) -> dict[str, Any]:
    # imported here: the route module imports this package's notifications
    from src.api.routes.anime import _fetch_and_store_relations

    now = int(time.time())
    checked = candidates = 0
    async with SessionLocal() as db:
        user_ids = (await db.execute(select(User.id))).scalars().all()
        for user_id in user_ids:
            prefs = await load_preferences(db, user_id)
            if not (prefs["notify_sequel_announced"] or prefs["notify_extras_announced"]):
                continue
            if "anime" not in prefs["notify_media_types"]:
                continue
            rows = (
                (
                    await db.execute(
                        select(Anime)
                        .where(
                            Anime.user_id == user_id,
                            Anime.deleted_at.is_(None),
                            Anime.status.in_([AnimeStatus.WATCHED, AnimeStatus.FAVORITE]),
                            Anime.anilist_id.is_not(None),
                            or_(
                                Anime.relations_cached_at.is_(None),
                                Anime.relations_cached_at < now - RECHECK_AFTER_SECONDS,
                            )
                            if not force
                            else Anime.anilist_id.is_not(None),
                        )
                        .order_by(Anime.relations_cached_at.asc().nullsfirst())
                    )
                )
                .scalars()
                .all()
            )
            candidates += len(rows)
            covered: set[str] = set()
            fetched = 0
            for show in rows:
                if str(show.anilist_id) in covered:
                    continue
                if fetched >= MAX_FRANCHISES_PER_RUN:
                    break
                try:
                    result = await _fetch_and_store_relations(show, db)
                except Exception:  # one franchise failing must not stop the rest
                    logger.exception("Franchise check failed for %s", show.id)
                    continue
                fetched += 1
                checked += 1
                covered.update(str(node.get("id")) for node in result.get("chain", []))
    return {"checked": checked, "titles": candidates}
