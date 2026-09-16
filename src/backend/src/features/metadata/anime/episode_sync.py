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


async def fetch_episodes_with_fallback(
    external_id: str | None, anilist_id: str | None
) -> tuple[list[dict[str, Any]], list[str]]:
    """Jikan (richer data — synopsis, air dates) is tried first when
    `external_id` (MyAnimeList's id) is known; AniList's
    `streamingEpisodes` is tried next as a fallback (thinner data, but
    real titles/thumbnails) when Jikan fails or wasn't matched. Returns
    `(episodes, errors)` rather than raising, so a caller with no HTTP
    request behind it (the background refresh) can just log errors
    instead of needing to turn them into an HTTPException."""
    all_episodes: list[dict[str, Any]] = []
    errors: list[str] = []
    if external_id:
        try:
            all_episodes = await asyncio.to_thread(JikanClient().episodes, external_id)
        except JikanError as exc:
            errors.append(f"Jikan: {exc}")
    if not all_episodes and anilist_id:
        try:
            all_episodes = await asyncio.to_thread(AniListClient().episodes, anilist_id)
        except AniListError as exc:
            errors.append(f"AniList: {exc}")
    return all_episodes, errors


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


async def backfill_from_tmdb(
    all_episodes: list[dict[str, Any]], show_title: str, tmdb_api_key: str
) -> None:
    """Fill in title/description/air_date/still_url for whichever entries
    are still bare placeholders (neither Jikan nor AniList had them) —
    most long-running anime is also indexed as an ordinary TV show on
    TMDB, often more completely than AniList's sparse `streamingEpisodes`.
    Silently gives up on any TMDB failure; the placeholders it can't fill
    just stay as they are, no worse off than before this ran."""
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
        if entry.get("title") is not None:
            continue
        match = by_number.get(entry["episode_number"])
        if match:
            entry.update(match)
