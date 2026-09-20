"""Fetching a show's episode list from whichever provider has it, shared
between the on-demand route (api/routes/anime.py) and the weekly
background refresh (features/metadata/refresh.py) — one place for the
Jikan + AniList + Kitsu + TMDB merge instead of duplicating it."""

from __future__ import annotations

import asyncio
from typing import Any

from src.features.metadata.anime.anilist import AniListClient, AniListError
from src.features.metadata.anime.anizip import AniZipClient, AniZipError
from src.features.metadata.anime.jikan import JikanClient, JikanError
from src.features.metadata.anime.kitsu import KitsuClient, KitsuError
from src.features.metadata.movies.tmdb import TMDBClient, TMDBError


def _merge_episode_sources(*sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Combines any number of providers' episode lists by episode number
    instead of picking one — no single provider is complete. Jikan has
    real titles/synopses/air-dates but its v4 API has no per-episode
    image field at all; AniList's `streamingEpisodes` has thumbnails but
    no air date/synopsis and only thinly covers long-running shows;
    Kitsu has its own independent thumbnails and synopses with its own
    (also incomplete) coverage. Merged per field — the first source
    passed wins a field it has a value for, later sources only fill in
    whatever's still blank — so three thin sources add up to one much
    more complete one instead of each other's gaps staying permanent."""
    by_number: dict[int, dict[str, Any]] = {}
    for source in sources:
        for entry in source:
            existing = by_number.get(entry["episode_number"])
            if existing is None:
                by_number[entry["episode_number"]] = dict(entry)
                continue
            for key, value in entry.items():
                if value is not None and not existing.get(key):
                    existing[key] = value
    return sorted(by_number.values(), key=lambda e: e["episode_number"])


async def fetch_episodes_with_fallback(
    external_id: str | None, anilist_id: str | None, kitsu_id: str | None = None
) -> tuple[list[dict[str, Any]], list[str]]:
    """Fetches from every provider with a known id — Jikan (richer data —
    synopsis, air dates, but no episode images at all), AniList
    (`streamingEpisodes` — thumbnails, but thinner coverage), and Kitsu
    (its own independent thumbnails/synopses) — and merges them rather
    than using one as a strict fallback for another, so whatever one
    provider is structurally missing (Jikan's total lack of episode
    images, in particular) has two other chances to be filled in instead
    of staying permanently blank. Returns `(episodes, errors)` rather
    than raising, so a caller with no HTTP request behind it (the
    background refresh) can just log errors instead of needing to turn
    them into an HTTPException."""
    anizip_episodes: list[dict[str, Any]] = []
    jikan_episodes: list[dict[str, Any]] = []
    anilist_episodes: list[dict[str, Any]] = []
    kitsu_episodes: list[dict[str, Any]] = []
    errors: list[str] = []
    if anilist_id:
        # first: for an airing show this is the source that has the new
        # episode's real title, screenshot and synopsis soonest
        try:
            anizip_episodes = await asyncio.to_thread(AniZipClient().episodes, anilist_id)
        except AniZipError as exc:
            errors.append(f"ani.zip: {exc}")
    if external_id:
        try:
            jikan_episodes = await asyncio.to_thread(JikanClient().episodes, external_id)
        except JikanError as exc:
            errors.append(f"Jikan: {exc}")
    if anilist_id:
        try:
            anilist_episodes = await asyncio.to_thread(AniListClient().episodes, anilist_id)
        except AniListError as exc:
            errors.append(f"AniList: {exc}")
    if kitsu_id:
        try:
            kitsu_episodes = await asyncio.to_thread(KitsuClient().episodes, kitsu_id)
        except KitsuError as exc:
            errors.append(f"Kitsu: {exc}")
    if not anizip_episodes and not jikan_episodes and not anilist_episodes and not kitsu_episodes:
        return [], errors
    return (
        _merge_episode_sources(anizip_episodes, jikan_episodes, anilist_episodes, kitsu_episodes),
        errors,
    )


async def fetch_airing_status(
    anilist_id: str | None,
) -> tuple[int | None, bool, int | None, int | None, list[str]]:
    """`(aired_count, is_airing, next_episode_air_at, next_episode_number,
    errors)` — the cheap AniList query, no episode list at all. Used by
    the frequent airing-check loop; MyAnimeList/Jikan has no equivalent
    lightweight endpoint, so this only covers the AniList side (fine —
    it's specifically the ongoing-show case this exists for, and AniList
    tracks nextAiringEpisode where Jikan doesn't expose anything
    comparable)."""
    if not anilist_id:
        return None, False, None, None, []
    try:
        count, is_airing, air_at, next_number = await asyncio.to_thread(
            AniListClient().airing_status, anilist_id
        )
        return count, is_airing, air_at, next_number, []
    except AniListError as exc:
        return None, False, None, None, [f"AniList: {exc}"]


def pad_to_known_total(all_episodes: list[dict[str, Any]], episode_count: int | None) -> int | None:
    """Neither provider reliably lists every episode for a very
    long-running show — pad the rest as plain numbered placeholders up to
    `episode_count` (when known) so the checklist still covers the whole
    run. In place. Returns the total to store on the season (unchanged if
    already known, otherwise the highest episode number actually seen)."""
    known_numbers = {entry["episode_number"] for entry in all_episodes}
    if episode_count:
        for n in range(1, episode_count + 1):
            if n not in known_numbers:
                all_episodes.append({"episode_number": n})
        all_episodes.sort(key=lambda e: e["episode_number"])
        return episode_count
    if all_episodes:
        return max(known_numbers)
    return episode_count


_BACKFILLABLE_EPISODE_FIELDS = (
    "title",
    "description",
    "air_date",
    "runtime_minutes",
    "still_url",
)


def needs_tmdb_backfill(all_episodes: list[dict[str, Any]]) -> bool:
    """Whether any entry is still missing a field TMDB could fill —
    checked per field rather than just "no title yet", since an entry can
    already have a real title (from Jikan, which never returns an
    episode image at all) while still missing everything else."""
    return any(
        entry.get(field) is None for entry in all_episodes for field in _BACKFILLABLE_EPISODE_FIELDS
    )


async def backfill_from_tmdb(
    all_episodes: list[dict[str, Any]], show_title: str, tmdb_api_key: str
) -> None:
    """Fills in whichever of title/description/air_date/runtime/still_url
    is still blank on each entry — most long-running anime is also
    indexed as an ordinary TV show on TMDB, often with a still image even
    when Jikan+AniList together don't have one. Checked per field, not
    "does this entry have a title yet" — an entry can already have a real
    title (from Jikan, which never returns episode images at all) and
    still be missing everything else TMDB could fill in; the old
    title-only gate skipped those entirely, so an episode that resolved
    via Jikan could never get a thumbnail even once a TMDB key was
    configured. Never overwrites a field that already has a value.
    Silently gives up on any TMDB failure; the fields it can't fill just
    stay as they are, no worse off than before this ran."""
    try:
        client = TMDBClient(tmdb_api_key)
        tv_id = await asyncio.to_thread(client.find_tv_id, show_title)
        if tv_id is None:
            return
        tmdb_episodes = await asyncio.to_thread(client.tv_all_episodes, tv_id)
    except TMDBError:
        return
    by_number = {e["episode_number"]: e for e in tmdb_episodes}
    for entry in all_episodes:
        match = by_number.get(entry["episode_number"])
        if not match:
            continue
        for field in _BACKFILLABLE_EPISODE_FIELDS:
            if entry.get(field) is None and match.get(field) is not None:
                entry[field] = match[field]
