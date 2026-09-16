"""Daily background refresh of episode data for shows/anime that already
have episodes synced — catches newly aired episodes for shows still
airing. Same in-process asyncio loop pattern as the trash sweep
(features/trash/sweep.py) and automatic backups
(features/backup/scheduler.py): no new worker container, no new
dependency. Mostly appends episode numbers that aren't already stored
and enriches blank placeholders — a watched or rated episode is never
touched. The one exception: a still-blank placeholder beyond what the
source provider now says has actually aired gets pruned (see
_prune_unaired_episodes), since that only happens from a prior
miscalculation, never from a real episode disappearing."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import or_, select

from src.core.app_integrations import get_or_create_app_integration_settings
from src.core.crypto import decrypt_secret
from src.database.models.anime import Anime, AnimeEpisode, AnimeSeason
from src.database.models.tv_show import TVEpisode, TVSeason, TVShow
from src.database.session import SessionLocal
from src.features.metadata.anime.episode_sync import (
    backfill_from_tmdb,
    fetch_airing_status,
    fetch_episodes_with_fallback,
    pad_to_known_total,
)
from src.features.metadata.tv.episode_sync import fetch_is_airing, fetch_season_episodes

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 24 * 60 * 60
AIRING_CHECK_INTERVAL_SECONDS = 30 * 60


@dataclass
class TaskStatus:
    """In-memory only (resets on restart, same as every other bit of
    state these loops carry) — good enough for a "last run" display, not
    meant as a durable audit log."""

    enabled: bool
    last_run_at: int | None = None
    last_result: dict = field(default_factory=dict)


airing_check_status = TaskStatus(enabled=False)
full_refresh_status = TaskStatus(enabled=False)


def _add_episode(
    model: type[AnimeEpisode] | type[TVEpisode], season_id, entry: dict
) -> AnimeEpisode | TVEpisode:
    raw_air_date = entry.get("air_date")
    return model(
        season_id=season_id,
        episode_number=entry["episode_number"],
        title=entry.get("title"),
        description=entry.get("description"),
        air_date=date.fromisoformat(raw_air_date) if raw_air_date else None,
        runtime_minutes=entry.get("runtime_minutes"),
        still_url=entry.get("still_url"),
    )


def _enrich_episode(existing: AnimeEpisode | TVEpisode, entry: dict) -> bool:
    """Fill in whatever the placeholder row is still missing from a fresh
    fetch — title being the main gate (a row synced before a TMDB key
    existed stays a bare "Episode N" until this runs again), but any
    other still-blank field is picked up too. Never overwrites a field
    that's already set. Returns whether anything actually changed."""
    changed = False
    if existing.title is None and entry.get("title") is not None:
        existing.title = entry["title"]
        changed = True
    if existing.description is None and entry.get("description") is not None:
        existing.description = entry["description"]
        changed = True
    if existing.air_date is None and entry.get("air_date"):
        existing.air_date = date.fromisoformat(entry["air_date"])
        changed = True
    if existing.runtime_minutes is None and entry.get("runtime_minutes") is not None:
        existing.runtime_minutes = entry["runtime_minutes"]
        changed = True
    if existing.still_url is None and entry.get("still_url") is not None:
        existing.still_url = entry["still_url"]
        changed = True
    return changed


def _prune_unaired_episodes(season: AnimeSeason, valid_numbers: set[int]) -> int:
    """Removes a still-blank placeholder row whose episode number the
    source provider no longer includes as aired — the only way that
    happens is a prior aired-count miscalculation created it too early
    (e.g. padding to a season's confirmed total instead of how many had
    actually aired). Never touches a watched or rated episode, and only
    called after a successful fetch, so a transient provider hiccup
    can't be mistaken for episodes disappearing."""
    removed = 0
    for episode in list(season.episodes):
        if episode.episode_number in valid_numbers:
            continue
        if episode.watched or episode.rating is not None:
            continue
        if episode.title is not None:
            continue
        season.episodes.remove(episode)
        removed += 1
    return removed


async def _refresh_anime_season(db, show: Anime, season: AnimeSeason) -> tuple[int, int]:
    """Returns (added, enriched) — added is brand-new episode numbers
    that didn't exist yet; enriched is existing bare placeholder rows
    that just got a real title/image now that better data is available
    (e.g. a TMDB key was added after the first sync)."""
    if not (show.external_id or show.anilist_id):
        return 0, 0
    all_episodes, errors = await fetch_episodes_with_fallback(show.external_id, show.anilist_id)
    if errors:
        logger.warning("Anime refresh couldn't reach a provider for %r: %s", show.title, "; ".join(errors))
    if not all_episodes:
        return 0, 0
    # Pad gaps up to THIS fetch's own highest episode number, never the
    # season's stored total — feeding that back in would re-inflate every
    # fresh fetch back up to the same wrong number forever (e.g. once
    # padded to a confirmed-but-not-fully-aired count before that bug
    # was fixed).
    fresh_total = max((e["episode_number"] for e in all_episodes), default=None)
    season.episode_count = pad_to_known_total(all_episodes, fresh_total)
    if any(e.get("title") is None for e in all_episodes):
        app_integrations = await get_or_create_app_integration_settings(db)
        if app_integrations.tmdb_api_key:
            tmdb_api_key = decrypt_secret(app_integrations.tmdb_api_key)
            await backfill_from_tmdb(all_episodes, show.title, tmdb_api_key)
    existing_by_number = {e.episode_number: e for e in season.episodes}
    added = 0
    enriched = 0
    for entry in all_episodes:
        existing = existing_by_number.get(entry["episode_number"])
        if existing is None:
            db.add(_add_episode(AnimeEpisode, season.id, entry))
            added += 1
        elif _enrich_episode(existing, entry):
            enriched += 1
    if not errors:
        _prune_unaired_episodes(season, {e["episode_number"] for e in all_episodes})
    return added, enriched


async def _quick_check_anime_season(show: Anime, season: AnimeSeason) -> int:
    """The frequent, cheap check: just asks AniList how many episodes
    have aired (and whether it's still airing at all), and if the count
    has gone up, adds bare numbered placeholder rows (no title/thumbnail
    yet) for the gap so there's something to check off right away — a
    checklist row appearing within AIRING_CHECK_INTERVAL_SECONDS of an
    episode airing, not the next full refresh. The full daily/manual
    refresh is what fills these in with real titles and images later.
    Only works for anime; MyAnimeList/Jikan has no comparably cheap
    endpoint. Persists `show.is_airing` either way, so a finished show
    gets excluded from this query entirely on the next pass."""
    if not show.anilist_id:
        return 0
    aired_total, is_airing, errors = await fetch_airing_status(show.anilist_id)
    if errors:
        logger.warning("Airing check couldn't reach AniList for %r: %s", show.title, "; ".join(errors))
        return 0
    show.is_airing = is_airing
    if not aired_total:
        return 0
    known_max = max((e.episode_number for e in season.episodes), default=0)
    if aired_total <= known_max:
        return 0
    added = 0
    for n in range(known_max + 1, aired_total + 1):
        season.episodes.append(AnimeEpisode(season_id=season.id, episode_number=n))
        added += 1
    if season.episode_count is None or season.episode_count < aired_total:
        season.episode_count = aired_total
    return added


async def _quick_check_tv_season(show: TVShow, season: TVSeason, db) -> int:
    """The frequent, cheap check for TV: first asks TVmaze just the
    show's status (a single small object) and persists `show.is_airing`
    from it. Only when it's actually still running does it bother with
    the (still cheap, but heavier) full episode fetch — a finished show
    gets excluded from the query entirely on the next pass instead of
    being re-fetched every cycle forever."""
    if not show.external_id:
        return 0
    is_airing, errors = await fetch_is_airing(show.external_id)
    if errors:
        logger.warning("Airing check couldn't reach TVmaze for %r: %s", show.title, "; ".join(errors))
        return 0
    if is_airing is not None:
        show.is_airing = is_airing
    if is_airing is False:
        return 0
    added, _enriched = await _refresh_tv_season(show, season, db)
    return added


async def _refresh_tv_season(show: TVShow, season: TVSeason, db) -> tuple[int, int]:
    """Returns (added, enriched) — TV rarely has bare placeholders (no
    padding step for TV, unlike anime), but the same enrich pass runs
    anyway so a row TVmaze had gaps in the first time still gets picked
    up if the gap closes later."""
    if not show.external_id:
        return 0, 0
    all_episodes, errors = await fetch_season_episodes(show.external_id, season.season_number)
    if errors:
        logger.warning("TV refresh couldn't reach TVmaze for %r: %s", show.title, "; ".join(errors))
    existing_by_number = {e.episode_number: e for e in season.episodes}
    added = 0
    enriched = 0
    for entry in all_episodes:
        existing = existing_by_number.get(entry["episode_number"])
        if existing is None:
            db.add(_add_episode(TVEpisode, season.id, entry))
            added += 1
        elif _enrich_episode(existing, entry):
            enriched += 1
    return added, enriched


async def refresh_all_episode_metadata() -> dict[str, int]:
    """Re-check every already-synced season (anime + TV): appends newly
    aired episode numbers, and separately enriches existing bare
    placeholder rows (title still null) whose data has since become
    available — e.g. a TMDB key added after the first sync. Only seasons
    someone has actually opened the Episodes tab for (i.e. already have
    at least one episode row) are refreshed — no point calling out for a
    show nobody's tracking episode-by-episode yet."""
    anime_added = anime_enriched = 0
    tv_added = tv_enriched = 0
    async with SessionLocal() as db:
        anime_seasons = (
            (await db.execute(select(AnimeSeason).join(Anime).where(Anime.deleted_at.is_(None))))
            .scalars()
            .all()
        )
        for anime_season in anime_seasons:
            if not anime_season.episodes:
                continue
            anime_show = await db.get(Anime, anime_season.show_id)
            if anime_show is None:
                continue
            try:
                added, enriched = await _refresh_anime_season(db, anime_show, anime_season)
                anime_added += added
                anime_enriched += enriched
            except Exception:
                logger.exception("Anime episode refresh failed for %s", anime_show.title)

        tv_seasons = (
            (await db.execute(select(TVSeason).join(TVShow).where(TVShow.deleted_at.is_(None))))
            .scalars()
            .all()
        )
        for tv_season in tv_seasons:
            if not tv_season.episodes:
                continue
            tv_show = await db.get(TVShow, tv_season.show_id)
            if tv_show is None:
                continue
            try:
                added, enriched = await _refresh_tv_season(tv_show, tv_season, db)
                tv_added += added
                tv_enriched += enriched
            except Exception:
                logger.exception("TV episode refresh failed for %s", tv_show.title)

        await db.commit()

    if anime_added or tv_added or anime_enriched or tv_enriched:
        logger.info(
            "Episode refresh: +%d/updated %d anime episode(s), +%d/updated %d TV episode(s)",
            anime_added,
            anime_enriched,
            tv_added,
            tv_enriched,
        )
    result = {
        "anime_episodes_added": anime_added,
        "anime_episodes_updated": anime_enriched,
        "tv_episodes_added": tv_added,
        "tv_episodes_updated": tv_enriched,
    }
    full_refresh_status.last_run_at = int(time.time())
    full_refresh_status.last_result = result
    return result


async def run_metadata_refresh_loop() -> None:
    full_refresh_status.enabled = True
    while True:
        try:
            await refresh_all_episode_metadata()
        except Exception:
            logger.exception("Daily metadata refresh loop failed")
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


async def check_airing_episodes() -> dict[str, int]:
    """The frequent, lightweight pass — filtered at the query level to
    shows that are airing or not yet checked (`is_airing` true or null);
    a show already known to have finished is skipped entirely, not just
    fetched-and-ignored. Anime gets the cheap aired-count-only check
    (_quick_check_anime_season); TV checks a cheap status field first and
    only fetches episodes if still running (_quick_check_tv_season).
    Neither does the (comparatively expensive) TMDB backfill step — that
    stays on the slower full refresh, run manually or via the daily
    loop."""
    anime_added = 0
    tv_added = 0
    async with SessionLocal() as db:
        anime_seasons = (
            (
                await db.execute(
                    select(AnimeSeason)
                    .join(Anime)
                    .where(
                        Anime.deleted_at.is_(None),
                        or_(Anime.is_airing.is_(True), Anime.is_airing.is_(None)),
                    )
                )
            )
            .scalars()
            .all()
        )
        for anime_season in anime_seasons:
            if not anime_season.episodes:
                continue
            anime_show = await db.get(Anime, anime_season.show_id)
            if anime_show is None:
                continue
            try:
                anime_added += await _quick_check_anime_season(anime_show, anime_season)
            except Exception:
                logger.exception("Airing check failed for anime %s", anime_show.title)

        tv_seasons = (
            (
                await db.execute(
                    select(TVSeason)
                    .join(TVShow)
                    .where(
                        TVShow.deleted_at.is_(None),
                        or_(TVShow.is_airing.is_(True), TVShow.is_airing.is_(None)),
                    )
                )
            )
            .scalars()
            .all()
        )
        for tv_season in tv_seasons:
            if not tv_season.episodes:
                continue
            tv_show = await db.get(TVShow, tv_season.show_id)
            if tv_show is None:
                continue
            try:
                tv_added += await _quick_check_tv_season(tv_show, tv_season, db)
            except Exception:
                logger.exception("Airing check failed for TV show %s", tv_show.title)

        await db.commit()

    if anime_added or tv_added:
        logger.info(
            "Airing check added %d anime episode(s), %d TV episode(s)", anime_added, tv_added
        )
    result = {"anime_episodes_added": anime_added, "tv_episodes_added": tv_added}
    airing_check_status.last_run_at = int(time.time())
    airing_check_status.last_result = result
    return result


async def run_airing_check_loop() -> None:
    airing_check_status.enabled = True
    while True:
        try:
            await check_airing_episodes()
        except Exception:
            logger.exception("Airing check loop failed")
        await asyncio.sleep(AIRING_CHECK_INTERVAL_SECONDS)
