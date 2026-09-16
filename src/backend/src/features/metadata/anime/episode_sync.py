"""Fetching a show's episode list from whichever provider has it, shared
between the on-demand route (api/routes/anime.py) and the weekly
background refresh (features/metadata/refresh.py) — one place for the
Jikan -> AniList -> TMDB fallback chain instead of duplicating it."""

from __future__ import annotations

import asyncio
from typing import Any

from src.features.metadata.anime.anilist import AniListClient, AniListError
from src.features.metadata.anime.jikan import JikanClient, JikanError
from src.features.metadata.movies.tmdb import TMDBClient, TMDBError


def _merge_episode_sources(
    jikan_episodes: list[dict[str, Any]], anilist_episodes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Combines both providers' episode lists by episode number instead
    of picking one — neither provider alone is complete. Jikan has real
    titles/synopses/air-dates but its v4 API has no per-episode image
    field at all (`still_url` is always null from `JikanClient.episodes`);
    AniList's `streamingEpisodes` has thumbnails but no air date/synopsis,
    and only thinly covers long-running shows. Merged per field, keeping
    whichever source already has a value for the fields Jikan won under
    the old either-or fallback (title/description/air_date/runtime) and
    filling in AniList's data (chiefly `still_url`) for whatever's still
    blank — this is the fix for episodes syncing with a real title but a
    permanently missing thumbnail."""
    by_number: dict[int, dict[str, Any]] = {
        entry["episode_number"]: dict(entry) for entry in anilist_episodes
    }
    for entry in jikan_episodes:
        existing = by_number.get(entry["episode_number"])
        if existing is None:
            by_number[entry["episode_number"]] = dict(entry)
            continue
        for key, value in entry.items():
            if value is not None and not existing.get(key):
                existing[key] = value
    return sorted(by_number.values(), key=lambda e: e["episode_number"])


async def fetch_episodes_with_fallback(
    external_id: str | None, anilist_id: str | None
) -> tuple[list[dict[str, Any]], list[str]]:
    """Fetches from both Jikan (richer data — synopsis, air dates, but no
    episode images) and AniList (`streamingEpisodes` — thumbnails, but
    thinner coverage) whenever both ids are known, and merges them rather
    than using one as a strict fallback for the other — using only one
    left whatever that provider was structurally missing (usually
    Jikan's total lack of episode images) permanently unfillable even
    after the other provider had the data all along. Returns
    `(episodes, errors)` rather than raising, so a caller with no HTTP
    request behind it (the background refresh) can just log errors
    instead of needing to turn them into an HTTPException."""
    jikan_episodes: list[dict[str, Any]] = []
    anilist_episodes: list[dict[str, Any]] = []
    errors: list[str] = []
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
    if not jikan_episodes and not anilist_episodes:
        return [], errors
    return _merge_episode_sources(jikan_episodes, anilist_episodes), errors


async def fetch_airing_status(
    anilist_id: str | None,
) -> tuple[int | None, bool, list[str]]:
    """`(aired_count, is_airing, errors)` — the cheap AniList query, no
    episode list at all. Used by the frequent airing-check loop;
    MyAnimeList/Jikan has no equivalent lightweight endpoint, so this
    only covers the AniList side (fine — it's specifically the
    ongoing-show case this exists for, and AniList tracks
    nextAiringEpisode where Jikan doesn't expose anything comparable)."""
    if not anilist_id:
        return None, False, []
    try:
        count, is_airing = await asyncio.to_thread(AniListClient().airing_status, anilist_id)
        return count, is_airing, []
    except AniListError as exc:
        return None, False, [f"AniList: {exc}"]


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
        entry.get(field) is None
        for entry in all_episodes
        for field in _BACKFILLABLE_EPISODE_FIELDS
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
