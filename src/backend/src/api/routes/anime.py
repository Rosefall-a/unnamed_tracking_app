"""API routes for managing anime and their seasons."""

import asyncio
import re
import time
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.anime import (
    AnimeCreate,
    AnimeRead,
    AnimeUpdate,
    EpisodeUpdate,
    SeasonCreate,
    SeasonUpdate,
)
from src.core.app_integrations import get_or_create_app_integration_settings
from src.core.auth import get_current_user
from src.core.crypto import decrypt_secret
from src.database.models.anime import Anime, AnimeEpisode, AnimeSeason, AnimeStatus
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.anime.anilist import AniListClient, AniListError
from src.features.metadata.anime.episode_sync import (
    backfill_from_tmdb,
    fetch_episodes_with_fallback,
    pad_to_known_total,
)
from src.features.metadata.anime.search import search_anime_metadata

router = APIRouter(prefix="/api/anime", tags=["anime"], dependencies=[Depends(get_current_user)])


class AnimeMetadataSearchResponse(BaseModel):
    query: str
    providers: list[str]
    provider_errors: list[str] = []
    results: list[dict]

_LEADING_ARTICLE = re.compile(r"^(a|an|the)\s+", flags=re.IGNORECASE)


def _derive_sort_title(title: str) -> str:
    """'The Melancholy of Haruhi Suzumiya' -> 'melancholy of haruhi suzumiya'."""
    return _LEADING_ARTICLE.sub("", title).strip().lower()


async def _get_show_or_404(
    show_id: UUID, db: AsyncSession, user_id: UUID, include_deleted: bool = False
) -> Anime:
    # populate_existing: a show already in this session's identity map
    # (e.g. loaded earlier in the same request, before a season was just
    # added to it) would otherwise keep its stale, already-cached
    # `seasons` collection instead of picking up the new row
    stmt = (
        select(Anime)
        .where(Anime.id == show_id, Anime.user_id == user_id)
        .execution_options(populate_existing=True)
    )
    if not include_deleted:
        stmt = stmt.where(Anime.deleted_at.is_(None))
    show = await db.scalar(stmt)
    if show is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Anime {show_id} not found")
    return show


async def _get_season_or_404(season_id: UUID, show_id: UUID, db: AsyncSession) -> AnimeSeason:
    season = await db.scalar(
        select(AnimeSeason).where(AnimeSeason.id == season_id, AnimeSeason.show_id == show_id)
    )
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Season {season_id} not found")
    return season


@router.get("/metadata/search", response_model=AnimeMetadataSearchResponse)
async def search_metadata(
    query: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(default=8, ge=1, le=20),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Search AniList and Jikan (MyAnimeList) for data that can prefill a
    new entry. Both are public/keyless — no app-wide credentials needed,
    unlike Movies/TV's TMDB and OMDb."""
    del current_user
    try:
        result = await asyncio.to_thread(search_anime_metadata, query.strip(), limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Metadata providers could not be reached: {exc}",
        ) from exc
    return result


@router.post("/create", response_model=AnimeRead, status_code=status.HTTP_201_CREATED)
async def create_anime(
    payload: AnimeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Anime:
    """Create an anime entry, optionally bulk-creating its seasons in the
    same transaction. If `seasons` is omitted entirely (not just an empty
    list), a default "Season 1" is created automatically — most anime
    never gets a second season added by hand, unlike TV shows."""
    data = payload.model_dump(exclude={"seasons"})
    if not data.get("sort_title"):
        data["sort_title"] = _derive_sort_title(data["title"])

    show = Anime(**data, user_id=current_user.id)
    db.add(show)
    await db.flush()

    if payload.seasons is None:
        db.add(AnimeSeason(season_number=1, show_id=show.id))
    else:
        for season_input in payload.seasons:
            db.add(AnimeSeason(**season_input.model_dump(), show_id=show.id))

    await db.commit()
    return await _get_show_or_404(show.id, db, current_user.id)


@router.get("/list", response_model=list[AnimeRead])
async def list_anime(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: AnimeStatus | None = Query(default=None, alias="status"),
    favorite: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="Case-insensitive title search"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Anime]:
    """Return the current user's anime, filtered by status, favorite flag, or title search."""
    stmt = select(Anime).where(Anime.user_id == current_user.id, Anime.deleted_at.is_(None))

    if status_filter is not None:
        stmt = stmt.where(Anime.status == status_filter)
    if favorite is not None:
        stmt = stmt.where(Anime.favorite == favorite)
    if search:
        stmt = stmt.where(Anime.title.ilike(f"%{search}%"))

    stmt = stmt.order_by(Anime.sort_title).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


@router.get("/get/{show_id}", response_model=AnimeRead)
async def get_anime(
    show_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Anime:
    """Return one anime by ID, with its seasons."""
    return await _get_show_or_404(show_id, db, current_user.id)


@router.patch("/update/{show_id}", response_model=AnimeRead)
async def update_anime(
    show_id: UUID,
    payload: AnimeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Anime:
    """Update an anime entry and keep its derived sort title synchronized."""
    show = await _get_show_or_404(show_id, db, current_user.id)

    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(show, field, value)

    if "title" in updates and "sort_title" not in updates:
        show.sort_title = _derive_sort_title(show.title)

    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.delete("/delete/{show_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_anime(
    show_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft-delete an anime entry by ID (its seasons stay attached, hidden along with it)."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    show.deleted_at = int(time.time())
    await db.commit()


@router.post("/{show_id}/seasons", response_model=AnimeRead, status_code=status.HTTP_201_CREATED)
async def create_season(
    show_id: UUID,
    payload: SeasonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Anime:
    show = await _get_show_or_404(show_id, db, current_user.id)
    db.add(AnimeSeason(**payload.model_dump(), show_id=show.id))
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.patch("/{show_id}/seasons/{season_id}", response_model=AnimeRead)
async def update_season(
    show_id: UUID,
    season_id: UUID,
    payload: SeasonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Anime:
    await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(season, field, value)

    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.delete("/{show_id}/seasons/{season_id}", response_model=AnimeRead)
async def delete_season(
    show_id: UUID,
    season_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Anime:
    await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)
    await db.delete(season)
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


async def _backfill_from_tmdb_if_configured(
    all_episodes: list[dict[str, Any]], show_title: str, db: AsyncSession
) -> None:
    app_integrations = await get_or_create_app_integration_settings(db)
    if app_integrations.tmdb_api_key:
        tmdb_api_key = decrypt_secret(app_integrations.tmdb_api_key)
        await backfill_from_tmdb(all_episodes, show_title, tmdb_api_key)


async def _get_episode_or_404(episode_id: UUID, season_id: UUID, db: AsyncSession) -> AnimeEpisode:
    episode = await db.scalar(
        select(AnimeEpisode).where(AnimeEpisode.id == episode_id, AnimeEpisode.season_id == season_id)
    )
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Episode {episode_id} not found")
    return episode


@router.get("/{show_id}/seasons/{season_id}/episodes", response_model=AnimeRead)
async def list_episodes(
    show_id: UUID,
    season_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Anime:
    """Return the season's episodes, syncing them in on the very first
    request. Jikan (richer data — synopsis, air dates) is tried first when
    the show has an `external_id`; if Jikan is unreachable or the show was
    never matched on MyAnimeList, AniList's `streamingEpisodes` is tried
    next as a fallback (thinner data — no air date/synopsis, but real
    titles and thumbnails) when an `anilist_id` is known. Nothing to sync
    from if neither id is set (added by hand, or found by neither
    provider). Every later call reads straight from the table instead of
    re-fetching."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)

    if not season.episodes and (show.external_id or show.anilist_id):
        all_episodes, errors = await fetch_episodes_with_fallback(
            show.external_id, show.anilist_id
        )
        if not all_episodes and errors:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not sync episodes: {'; '.join(errors)}",
            )
        season.episode_count = pad_to_known_total(all_episodes, season.episode_count)
        if any(e.get("title") is None for e in all_episodes):
            await _backfill_from_tmdb_if_configured(all_episodes, show.title, db)
        for entry in all_episodes:
            raw_air_date = entry.get("air_date")
            db.add(
                AnimeEpisode(
                    season_id=season.id,
                    episode_number=entry["episode_number"],
                    title=entry.get("title"),
                    description=entry.get("description"),
                    air_date=date.fromisoformat(raw_air_date) if raw_air_date else None,
                    runtime_minutes=entry.get("runtime_minutes"),
                    still_url=entry.get("still_url"),
                )
            )
        await db.commit()

    return await _get_show_or_404(show_id, db, current_user.id)


@router.patch("/{show_id}/seasons/{season_id}/episodes/{episode_id}", response_model=AnimeRead)
async def update_episode(
    show_id: UUID,
    season_id: UUID,
    episode_id: UUID,
    payload: EpisodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Anime:
    await _get_show_or_404(show_id, db, current_user.id)
    await _get_season_or_404(season_id, show_id, db)
    episode = await _get_episode_or_404(episode_id, season_id, db)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(episode, field, value)

    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.get("/{show_id}/relations")
async def get_anime_relations(
    show_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """AniList's real relations graph (prequel/sequel/spin-off/etc) for
    the best title match — keyless, so unlike TV/Movie there's no
    "not configured" state to handle here."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    try:
        result = await asyncio.to_thread(
            AniListClient().relations_and_recommendations, show.title
        )
    except AniListError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AniList could not be reached: {exc}"
        ) from exc
    return {"related": result["relations"], "configured": True}


@router.get("/{show_id}/recommended")
async def get_anime_recommended(
    show_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    show = await _get_show_or_404(show_id, db, current_user.id)
    try:
        result = await asyncio.to_thread(
            AniListClient().relations_and_recommendations, show.title
        )
    except AniListError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AniList could not be reached: {exc}"
        ) from exc
    return {"recommended": result["recommendations"], "configured": True}
