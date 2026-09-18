"""Fetching a show's episode list from TVmaze, shared between the
on-demand route (api/routes/tv_shows.py) and the background refresh jobs
(features/metadata/refresh.py)."""

from __future__ import annotations

import asyncio
from typing import Any

from src.features.metadata.tv.tvmaze import TVMazeClient, TVMazeError


async def fetch_season_episodes(
    external_id: str | None, season_number: int
) -> tuple[list[dict[str, Any]], list[str]]:
    """TVmaze has no per-season endpoint — it returns every episode for
    the whole show in one call, so the result is filtered down to just
    the requested season here. Returns `(episodes, errors)` rather than
    raising, so a caller with no HTTP request behind it (the background
    refresh) can just log errors instead of needing an HTTPException."""
    if not external_id:
        return [], []
    try:
        all_episodes = await asyncio.to_thread(TVMazeClient().episodes, external_id)
    except TVMazeError as exc:
        return [], [f"TVmaze: {exc}"]
    return [e for e in all_episodes if e.get("season_number") == season_number], []


async def fetch_is_airing(external_id: str | None) -> tuple[bool | None, list[str]]:
    """Just the show's own status ("Running" vs. anything else) — a
    single small object, cheap enough to check before deciding whether
    the (still relatively cheap, but heavier) full episode list is worth
    fetching on a given pass. Returns `None` (unknown) rather than
    raising on failure, same reasoning as fetch_season_episodes."""
    if not external_id:
        return None, []
    try:
        raw_status = await asyncio.to_thread(TVMazeClient().show_status, external_id)
    except TVMazeError as exc:
        return None, [f"TVmaze: {exc}"]
    if raw_status is None:
        return None, []
    return raw_status == "Running", []


async def fetch_next_episode(
    external_id: str | None,
) -> tuple[int | None, int | None, list[str]]:
    """`(air_at_unix, episode_number, errors)` for the show's next
    scheduled episode — drives a countdown display and the calendar
    view, same as the AniList side does for anime."""
    if not external_id:
        return None, None, []
    try:
        air_at, number = await asyncio.to_thread(TVMazeClient().next_episode, external_id)
        return air_at, number, []
    except TVMazeError as exc:
        return None, None, [f"TVmaze: {exc}"]
