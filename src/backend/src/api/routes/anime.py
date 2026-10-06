"""API routes for managing anime and their seasons."""

import asyncio
import logging
import time
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.media_common import (
    LibraryFilters,
    library_page,
    owned_row,
    purge_row,
    related_row,
    request_metadata,
    restore_row,
    soft_delete,
    title_search,
    trash_listing,
    update_tracking,
)
from src.api.routes.media_extras import log_episode_progress
from src.api.schemas.anime import (
    AnimeCreate,
    AnimeLibraryRead,
    AnimeRead,
    AnimeUpdate,
    EpisodesBulkWatched,
    EpisodeUpdate,
    SeasonCreate,
    SeasonUpdate,
)
from src.api.schemas.metadata import MetadataSearchResponse
from src.api.schemas.pagination import LibraryQuery, PaginatedResponse
from src.core.app_integrations import get_or_create_app_integration_settings
from src.core.auth import get_current_user
from src.core.integrations import resolve_integrations
from src.core.titles import apply_alt_titles
from src.core.titles import derive_sort_title as _derive_sort_title
from src.database.models.anime import Anime, AnimeEpisode, AnimeSeason, AnimeStatus
from src.database.models.user import User
from src.database.session import SessionLocal, get_db
from src.features.episode_progress import (
    set_episodes_watched,
    update_episode_progress,
    update_season_progress,
)
from src.features.imports.anilist import import_anilist_library as apply_anilist_import
from src.features.metadata.anime.alt_titles import fill_missing_titles
from src.features.metadata.anime.anilist import RELATIONS_CACHE_VERSION, AniListClient, AniListError
from src.features.metadata.anime.episode_sync import (
    backfill_from_tmdb,
    fetch_episodes_with_fallback,
    needs_tmdb_backfill,
    pad_to_known_total,
)
from src.features.metadata.anime.search import (
    get_anime_metadata_by_anilist_id,
    search_anime_metadata,
)
from src.features.metadata.refresh import (
    merge_episodes,
    quick_check_anime_season,
    refresh_anime_season_now,
)
from src.features.notifications import record_sequel_announcements

_DB_DEFAULT = Depends(get_db)
_CURRENT_USER_DEFAULT = Depends(get_current_user)
_QUERY_DEFAULT = Query(..., min_length=2, max_length=100, alias="query")
_LIMIT_DEFAULT = Query(default=8, ge=1, le=20, alias="limit")


router = APIRouter(prefix="/api/anime", tags=["anime"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)

# fields the metadata search's "Apply" button can fill in — the only ones
# worth locking, since nothing else is ever set by that flow
_LOCKABLE_FIELDS = frozenset(
    {
        "title",
        "description",
        "first_air_date",
        "episode_runtime_minutes",
        "studios",
        "genres",
        "poster_url",
        "backdrop_url",
        "anilist_score",
        "mal_score",
    }
)


class AnimeMetadataSearchResponse(MetadataSearchResponse):
    # Keep the existing named HTTP schema; all data fields belong to its shared base.
    # pylint: disable=too-few-public-methods
    pass


async def _get_show_or_404(
    show_id: UUID, db: AsyncSession, user_id: UUID, include_deleted: bool = False
) -> Anime:
    return await owned_row(
        db,
        Anime,
        show_id,
        user_id,
        "Anime",
        include_deleted=include_deleted,
        populate_existing=True,
    )


async def _get_season_or_404(season_id: UUID, show_id: UUID, db: AsyncSession) -> AnimeSeason:
    return await related_row(
        db,
        AnimeSeason,
        season_id,
        parent_column=AnimeSeason.show_id,
        parent_id=show_id,
        label="Season",
    )


class AniListImportRequest(BaseModel):
    username: str
    update_existing: bool = False


class AniListImportResult(BaseModel):
    fetched: int
    created: int
    updated: int
    skipped: int
    errors: list[str] = []


@router.post("/import/anilist", response_model=AniListImportResult)
async def import_anilist_library(
    payload: AniListImportRequest,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> AniListImportResult:
    """Import a public AniList anime list without modifying AniList."""
    try:
        result = await apply_anilist_import(
            db, current_user.id, payload.username, payload.update_existing
        )
    except AniListError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return AniListImportResult(**result)


@router.get("/metadata/search", response_model=AnimeMetadataSearchResponse)
async def search_metadata(
    query: str = _QUERY_DEFAULT,
    limit: int = _LIMIT_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict:
    """Search AniList and Jikan (MyAnimeList) for data that can prefill a
    new entry. Both are public/keyless — no app-wide credentials needed,
    unlike Movies/TV's TMDB and OMDb."""
    del current_user
    result = await request_metadata(
        search_anime_metadata, "Metadata providers", query.strip(), limit
    )
    return result


@router.post("/fill-titles")
async def fill_alternate_titles(
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict:
    """Looks up the English, romaji and Japanese spelling of every anime of
    yours that has none stored yet (see alt_titles.fill_missing_titles). The
    media refresh does the same for everyone, so this is only needed to do it
    right now."""
    return await fill_missing_titles(db, current_user.id)


@router.get("/metadata/by-id/{anilist_id}", response_model=dict | None)
async def get_metadata_by_id(
    anilist_id: int,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict | None:
    """Looks up one exact AniList entry by id, in the same shape
    `/metadata/search` returns per result — used when adding a title from
    the Related/Recommended graph, which already carries a real AniList
    id and shouldn't need a fresh title search to find the same entry
    again (fragile for an unusual title, and wasted requests against an
    API with a real rate limit)."""
    del current_user
    result = await request_metadata(get_anime_metadata_by_anilist_id, "AniList", anilist_id)
    return result


@router.post("/create", response_model=AnimeRead, status_code=status.HTTP_201_CREATED)
async def create_anime(
    payload: AnimeCreate,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
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

    # keep the English/romaji/Japanese spellings when the entry has an AniList
    # id; best-effort, a slow AniList never blocks creation
    if (
        show.anilist_id
        and show.anilist_id.isdigit()
        and not (show.title_english or show.title_romaji or show.title_native)
    ):
        try:
            found, _ = await asyncio.to_thread(AniListClient().get_by_ids, [int(show.anilist_id)])
            if meta := found.get(int(show.anilist_id)):
                apply_alt_titles(show, meta)
        # Optional provider enrichment must not abort creation of the user's title.
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Alternate titles lookup failed for new anime %r", show.title)

    if payload.seasons is None:
        first_season = AnimeSeason(season_number=1, show_id=show.id)
        db.add(first_season)
    else:
        first_season = None
        for season_input in payload.seasons:
            season = AnimeSeason(**season_input.model_dump(), show_id=show.id)
            db.add(season)
            if first_season is None:
                first_season = season

    # Otherwise a freshly-added airing show shows no next-episode date
    # anywhere (countdown, calendar) until the next periodic airing-check
    # pass, up to one airing-check interval later — worth the one
    # extra AniList call at creation time so it's there immediately.
    # Best-effort: a slow/unreachable AniList never blocks creation.
    if show.anilist_id and first_season is not None:
        try:
            await quick_check_anime_season(show, first_season)
        # Optional provider enrichment must not abort creation of the user's title.
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Immediate airing check failed for new anime %r", show.title)

    await db.commit()
    if show.anilist_id:
        # store its franchise graph now, off the request, so Seasons/Related
        # are ready the first time the title is opened
        asyncio.create_task(refresh_relations_in_background(show.id))
    return await _get_show_or_404(show.id, db, current_user.id)


@router.post("/{show_id}/refresh-airing", response_model=AnimeRead)
async def refresh_airing(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Anime:
    """Runs the airing check for just this title right now (the background
    loop only comes around every 30 minutes) — updates the next-episode
    date/number and adds placeholder rows for anything newly aired."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    if not show.anilist_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This title has no AniList id, so its airing schedule can't be checked.",
        )
    if show.seasons:
        season = show.seasons[-1]
        await quick_check_anime_season(show, season)
        await refresh_anime_season_now(db, show, season)
        await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.get("/list", response_model=PaginatedResponse[AnimeLibraryRead])
async def list_anime(
    query: Annotated[LibraryQuery[AnimeStatus], Query()],
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> PaginatedResponse[AnimeLibraryRead]:
    """Return one page of the current user's anime and the total matching it."""
    return await library_page(
        db,
        Anime,
        current_user.id,
        skip=query.skip,
        limit=query.limit,
        filters=LibraryFilters.from_query(
            query,
            AnimeStatus,
            search_clause=title_search(
                [Anime.title, Anime.title_english, Anime.title_romaji, Anime.title_native],
                query.search,
            ),
            year_column=Anime.first_air_date,
        ),
    )


@router.get("/get/{show_id}", response_model=AnimeRead)
async def get_anime(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Anime:
    """Return one anime by ID, with its seasons."""
    return await _get_show_or_404(show_id, db, current_user.id)


@router.patch("/update/{show_id}", response_model=AnimeRead)
async def update_anime(
    show_id: UUID,
    payload: AnimeUpdate,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Anime:
    """Update an anime entry and keep its derived sort title synchronized."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    await update_tracking(
        db, show, payload.model_dump(exclude_unset=True), _LOCKABLE_FIELDS, "anime"
    )

    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.delete("/delete/{show_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_anime(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> None:
    """Soft-delete an anime entry by ID (its seasons stay attached, hidden along with it)."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    await soft_delete(db, show)


@router.get("/trash")
async def list_anime_trash(
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> list[dict]:
    """Deleted anime entries, most recently deleted first. No purge job
    runs against these — unlike Game's on-disk folders, an entry is just
    a row (plus its seasons/episodes), so there's nothing to clean up
    and it stays here until an admin either restores it or purges it."""
    return await trash_listing(db, Anime, current_user.id)


@router.post("/{show_id}/restore", response_model=AnimeRead)
async def restore_anime(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Anime:
    show = await _get_show_or_404(show_id, db, current_user.id, include_deleted=True)
    await restore_row(db, show, "Entry")
    return await _get_show_or_404(show_id, db, current_user.id)


@router.delete("/{show_id}/purge", status_code=status.HTTP_204_NO_CONTENT)
async def purge_anime(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> None:
    """Permanently removes an already-deleted anime entry and its
    seasons/episodes. Only reachable from trash — an entry still active
    must be soft-deleted first."""
    show = await _get_show_or_404(show_id, db, current_user.id, include_deleted=True)
    await purge_row(db, show, "Entry")


@router.post("/{show_id}/seasons", response_model=AnimeRead, status_code=status.HTTP_201_CREATED)
async def create_season(
    show_id: UUID,
    payload: SeasonCreate,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
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
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Anime:
    show = await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)

    newly_watched = update_season_progress(season, payload.model_dump(exclude_unset=True))
    await log_episode_progress(db, current_user.id, show, "anime", newly_watched)
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.delete("/{show_id}/seasons/{season_id}", response_model=AnimeRead)
async def delete_season(
    show_id: UUID,
    season_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Anime:
    await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)
    await db.delete(season)
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


async def _backfill_from_tmdb_if_configured(
    all_episodes: list[dict[str, Any]], show_title: str, db: AsyncSession
) -> None:
    app_integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
    if app_integrations.tmdb_api_key:
        tmdb_api_key = app_integrations.tmdb_api_key
        await backfill_from_tmdb(all_episodes, show_title, tmdb_api_key)


async def _get_episode_or_404(episode_id: UUID, season_id: UUID, db: AsyncSession) -> AnimeEpisode:
    return await related_row(
        db,
        AnimeEpisode,
        episode_id,
        parent_column=AnimeEpisode.season_id,
        parent_id=season_id,
        label="Episode",
    )


@router.get("/{show_id}/seasons/{season_id}/episodes", response_model=AnimeRead)
async def list_episodes(
    show_id: UUID,
    season_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Anime:
    """Return the season's episodes, syncing them in on the very first
    request. Fetches from every provider with a known id (Jikan, AniList,
    Kitsu) and merges their results per field rather than using one as a
    strict fallback for another — see `fetch_episodes_with_fallback`.
    Nothing to sync from if no id is set at all (added by hand, or found
    by no provider). Every later call reads straight from the table
    instead of re-fetching."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)

    if not season.episodes and (show.external_id or show.anilist_id or show.kitsu_id):
        fetch = await fetch_episodes_with_fallback(show.external_id, show.anilist_id, show.kitsu_id)
        all_episodes, errors = fetch.episodes, fetch.errors
        if fetch.kitsu_id and show.kitsu_id != fetch.kitsu_id:
            show.kitsu_id = fetch.kitsu_id
        if not all_episodes and errors:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not sync episodes: {'; '.join(errors)}",
            )
        # Pad gaps up to THIS fetch's own highest episode number, never
        # the season's stored total — feeding that back in would
        # re-inflate every fresh fetch back up to the same wrong number
        # forever (e.g. once padded to a confirmed-but-not-fully-aired
        # count before that bug was fixed).
        fresh_total = fetch.final_total or max(
            (e["episode_number"] for e in all_episodes), default=None
        )
        season.episode_count = pad_to_known_total(all_episodes, fresh_total)
        if needs_tmdb_backfill(all_episodes):
            await _backfill_from_tmdb_if_configured(all_episodes, show.title, db)
        # Initial listings preserve their existing date-only payload; timed refreshes also save air_at.
        merge_episodes(db, season, all_episodes, AnimeEpisode, include_air_at=False)
        await db.commit()

    return await _get_show_or_404(show_id, db, current_user.id)


@router.patch("/{show_id}/seasons/{season_id}/episodes/bulk-watched", response_model=AnimeRead)
async def bulk_set_episodes_watched(
    show_id: UUID,
    season_id: UUID,
    payload: EpisodesBulkWatched,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Anime:
    """Sets `watched` on a whole batch of episodes in one request — a
    shift-click range select or "mark watched up to here" would
    otherwise cost one PATCH per episode, which gets genuinely slow on a
    500+ episode season. Silently ignores any id that isn't actually in
    this season rather than 404ing the whole batch over one bad id.
    Registered ahead of the single-episode PATCH below so the literal
    path segment "bulk-watched" is matched here rather than attempted as
    an `episode_id` UUID."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)
    newly_watched = set_episodes_watched(season, set(payload.episode_ids), payload.watched)
    await log_episode_progress(db, current_user.id, show, "anime", newly_watched)
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.patch("/{show_id}/seasons/{season_id}/episodes/{episode_id}", response_model=AnimeRead)
async def update_episode(
    show_id: UUID,
    season_id: UUID,
    episode_id: UUID,
    payload: EpisodeUpdate,
    *,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Anime:
    show = await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)
    episode = await _get_episode_or_404(episode_id, season_id, db)

    newly_watched = update_episode_progress(season, episode, payload.model_dump(exclude_unset=True))

    await log_episode_progress(db, current_user.id, show, "anime", newly_watched)
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


# How long a cached Related/Recommended payload is served without
# re-asking AniList — a prequel/sequel chain or recommendation list
# changes rarely (only a genuine new-sequel announcement, or AniList
# recomputing its own recommendation scores), so most visits should cost
# zero AniList requests rather than a dozen+.
_RELATIONS_CACHE_TTL_SECONDS = 3 * 24 * 60 * 60


_relations_inflight: set[UUID] = set()


async def _fetch_and_store_relations(show: Anime, db: AsyncSession) -> dict:
    """Asks AniList (slow: a paced request per franchise entry), stores the
    result on the row, and notes any newly listed season for a title the
    user has completed."""
    old_chain = show.relations_cache.get("chain") if show.relations_cache else None
    result = await asyncio.to_thread(
        AniListClient().relations_chain_and_branches, show.title, show.anilist_id
    )
    show.relations_cache = result
    show.relations_cached_at = int(time.time())
    await db.commit()
    await record_sequel_announcements(db, show.user_id, show, old_chain, result["chain"])
    return result


async def refresh_relations_in_background(show_id: UUID) -> None:
    """Fetches and stores a franchise graph without making anyone wait for
    it. Used for a stale cache (the old one is served meanwhile) and to
    warm a title right after it is added, so its Seasons and Related tabs
    are already in the database by the time it is opened."""
    if show_id in _relations_inflight:
        return
    _relations_inflight.add(show_id)
    try:
        async with SessionLocal() as db:
            show = await db.scalar(select(Anime).where(Anime.id == show_id))
            if show is None or not show.anilist_id:
                return
            await _fetch_and_store_relations(show, db)
    # This background task reports its own failure and always releases the inflight marker.
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Background franchise refresh failed for %s", show_id)
    finally:
        _relations_inflight.discard(show_id)


async def _get_or_refresh_anime_relations(show: Anime, db: AsyncSession) -> dict:
    """Chain + branches + recommendations for one anime, straight from the
    database whenever anything is stored. A stale or older-layout copy is
    still served instantly and refreshed in the background, so opening a
    title never waits on AniList once it has been seen. Only a title with
    nothing stored yet has to wait for the first fetch."""
    cached = show.relations_cache
    if cached is not None:
        cache_age = (
            int(time.time()) - show.relations_cached_at if show.relations_cached_at else None
        )
        fresh = (
            cached.get("version") == RELATIONS_CACHE_VERSION
            and cache_age is not None
            and cache_age < _RELATIONS_CACHE_TTL_SECONDS
        )
        if not fresh:
            asyncio.create_task(refresh_relations_in_background(show.id))
        return cached
    return await _fetch_and_store_relations(show, db)


@router.get("/{show_id}/relations")
async def get_anime_relations(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict:
    """The full prequel/sequel chain this entry belongs to, plus every
    other relation (adaptation, side story, source manga/novel, etc.)
    attached to whichever chain entry it's actually connected to — not
    just this one entry's own direct relations, which for a 3+ season
    franchise would read as missing entries. Uses the stored AniList id
    when known (set at creation/sync) rather than re-searching by title,
    since a title search can match a different entry with a similar
    name. Keyless, so unlike TV/Movie there's no "not configured" state."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    try:
        result = await _get_or_refresh_anime_relations(show, db)
    except AniListError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AniList could not be reached: {exc}"
        ) from exc
    return {
        "chain": result["chain"],
        "branches": result["branches"],
        "configured": True,
    }


@router.get("/{show_id}/recommended")
async def get_anime_recommended(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict:
    """Reuses the same cached fetch `/relations` populates — AniList
    returns both a title's relations and its recommendations in one
    request, so there's no reason for this tab to cost a second one."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    try:
        result = await _get_or_refresh_anime_relations(show, db)
    except AniListError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AniList could not be reached: {exc}"
        ) from exc
    return {"recommended": result.get("recommendations", []), "configured": True}
