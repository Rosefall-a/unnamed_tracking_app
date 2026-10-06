"""Apply a normalized AniList public-list import to a user's library."""

import asyncio
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.anime import Anime, AnimeSeason
from src.features.metadata.anime.anilist_import import AniListImportClient


def _derive_sort_title(title: str) -> str:
    lowered = title.strip().lower()
    for article in ("a ", "an ", "the "):
        if lowered.startswith(article):
            return lowered[len(article) :]
    return lowered


def _import_fields(entry: dict[str, Any]) -> dict[str, Any]:
    fields = {
        field: entry[field]
        for field in (
            "title",
            "description",
            "episode_runtime_minutes",
            "studios",
            "countries",
            "genres",
            "format",
            "anilist_score",
            "poster_url",
            "backdrop_url",
            "status",
            "priority",
            "note",
            "rating_overall",
        )
    }
    for field in ("first_air_date", "start_date", "end_date"):
        fields[field] = date.fromisoformat(entry[field]) if entry[field] else None
    fields["rewatches"] = entry["repeat"]
    fields["sort_title"] = _derive_sort_title(entry["title"])
    return fields


async def _apply_entry(
    db: AsyncSession, user_id: UUID, entry: dict[str, Any], update_existing: bool
) -> str:
    show = await db.scalar(
        select(Anime).where(
            Anime.user_id == user_id,
            Anime.anilist_id == entry["anilist_id"],
            Anime.deleted_at.is_(None),
        )
    )
    if show is not None and not update_existing:
        return "skipped"
    outcome = "created" if show is None else "updated"
    fields = _import_fields(entry)
    season: AnimeSeason | None
    if show is None:
        show = Anime(
            user_id=user_id,
            anilist_id=entry["anilist_id"],
            languages=[],
            tags=[],
            features=[],
            **fields,
        )
        db.add(show)
        await db.flush()
        season = AnimeSeason(show_id=show.id, season_number=1)
        db.add(season)
    else:
        for field, value in fields.items():
            setattr(show, field, value)
        season = show.seasons[0] if show.seasons else None
        if season is None:
            season = AnimeSeason(show_id=show.id, season_number=1)
            db.add(season)
    season.episode_count = entry["episode_count"]
    season.episodes_watched = entry["progress"]
    season.status = entry["status"]
    await db.commit()
    return outcome


async def import_anilist_library(
    db: AsyncSession, user_id: UUID, username: str, update_existing: bool = False
) -> dict[str, Any]:
    """Fetch and apply one public AniList list. The caller owns the session."""
    entries = await asyncio.to_thread(AniListImportClient().fetch_user_anime, username)
    result: dict[str, Any] = {
        "fetched": len(entries),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }
    for entry in entries:
        try:
            outcome = await _apply_entry(db, user_id, entry, update_existing)
            result[outcome] += 1
        except (SQLAlchemyError, ValueError, TypeError, KeyError) as exc:
            await db.rollback()
            result["skipped"] += 1
            result["errors"].append(f"{entry.get('title', 'Unknown title')}: {exc}")
    result["errors"] = result["errors"][:20]
    return result
