"""Filling in an anime's English, romaji and Japanese spellings from AniList,
in batches (50 titles a request). Shared by the "look up titles" button and
the media refresh, so a title added or imported without them gets them on the
next refresh. Only blank title fields are set, nothing else changes."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.titles import apply_alt_titles
from src.database.models.anime import Anime
from src.features.metadata.anime.anilist import AniListClient


async def fill_missing_titles(db: AsyncSession, user_id: UUID | None = None) -> dict[str, Any]:
    """Looks up every anime (one user's, or everyone's) that has none of the
    three spellings. Titles with neither an AniList nor a MyAnimeList id cannot
    be looked up and are counted."""
    stmt = select(Anime).where(
        Anime.deleted_at.is_(None),
        Anime.title_english.is_(None),
        Anime.title_romaji.is_(None),
        Anime.title_native.is_(None),
    )
    if user_id is not None:
        stmt = stmt.where(Anime.user_id == user_id)
    shows = list((await db.execute(stmt)).scalars().all())
    client = AniListClient()
    anilist_ids = [int(s.anilist_id) for s in shows if s.anilist_id and s.anilist_id.isdigit()]
    mal_ids = [
        int(s.external_id)
        for s in shows
        if not s.anilist_id and s.external_id and s.external_id.isdigit()
    ]
    by_anilist, failed_a = (
        await asyncio.to_thread(client.get_by_ids, anilist_ids) if anilist_ids else ({}, 0)
    )
    by_mal, failed_m = (
        await asyncio.to_thread(client.get_by_mal_ids, mal_ids) if mal_ids else ({}, 0)
    )
    filled = 0
    for show in shows:
        meta = None
        if show.anilist_id and show.anilist_id.isdigit():
            meta = by_anilist.get(int(show.anilist_id))
        elif show.external_id and show.external_id.isdigit():
            meta = by_mal.get(int(show.external_id))
        if meta and apply_alt_titles(show, meta):
            filled += 1
    await db.commit()
    return {
        "filled": filled,
        "without_id": sum(1 for s in shows if not s.anilist_id and not s.external_id),
        "lookup_failed": failed_a + failed_m,
        "checked": len(shows),
    }
