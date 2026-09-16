from __future__ import annotations

import re
from typing import Any

import requests

_BASE_URL = "https://api.jikan.moe/v4"
_DURATION_RE = re.compile(r"(\d+)")


class JikanError(RuntimeError):
    """Raised when Jikan (the unofficial MyAnimeList API) responds unsuccessfully."""


def _parse_duration(value: str | None) -> int | None:
    """Jikan reports duration as a free-text string, e.g. '24 min per ep'."""
    if not value:
        return None
    match = _DURATION_RE.search(value)
    return int(match.group(1)) if match else None


class JikanClient:
    """Minimal client for Jikan v4 (an unofficial, public MyAnimeList API
    wrapper). No authentication required — MAL itself has no public
    search API, so this is the closest keyless equivalent. Kept as the
    secondary/fallback source alongside AniList for the same redundancy
    Movies/TV get from TMDB+OMDb."""

    def __init__(self, *, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        try:
            response = self.session.get(
                f"{_BASE_URL}/anime",
                params={"q": query, "limit": str(limit)},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise JikanError(f"Could not reach Jikan: {exc}") from exc
        if response.status_code >= 400:
            raise JikanError(f"Jikan request failed ({response.status_code}): {response.text[:200]}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise JikanError("Jikan returned invalid JSON.") from exc
        if payload.get("status") and payload.get("status") != 200:
            raise JikanError(payload.get("message", "Jikan returned an error."))

        candidates = payload.get("data") or []
        results: list[dict[str, Any]] = []
        for entry in candidates[:limit]:
            images = ((entry.get("images") or {}).get("jpg")) or {}
            aired = (entry.get("aired") or {}).get("from")
            results.append(
                {
                    "id": entry.get("mal_id"),
                    "title": entry.get("title_english") or entry.get("title"),
                    "overview": entry.get("synopsis"),
                    "release_date": aired.split("T")[0] if aired else None,
                    "episode_runtime_minutes": _parse_duration(entry.get("duration")),
                    "episode_count": entry.get("episodes"),
                    "studios": [s["name"] for s in entry.get("studios", []) if s.get("name")],
                    "countries": [],
                    "genres": [g["name"] for g in entry.get("genres", []) if g.get("name")],
                    "poster_url": images.get("large_image_url") or images.get("image_url"),
                    "score": entry.get("score"),
                    # Jikan's "type" is already the friendly label we want:
                    # TV, Movie, OVA, ONA, Special, Music.
                    "format": entry.get("type"),
                    "url": entry.get("url"),
                }
            )
        return results

    def episodes(self, mal_id: str) -> list[dict[str, Any]]:
        """Jikan's episode list is thinner than TVmaze's — no thumbnail or
        synopsis per episode, just number/title/air date — but it's the
        only keyless per-episode source available for anime."""
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            try:
                response = self.session.get(
                    f"{_BASE_URL}/anime/{mal_id}/episodes",
                    params={"page": str(page)},
                    timeout=15,
                )
            except requests.RequestException as exc:
                raise JikanError(f"Could not reach Jikan: {exc}") from exc
            if response.status_code >= 400:
                raise JikanError(
                    f"Jikan request failed ({response.status_code}): {response.text[:200]}"
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise JikanError("Jikan returned invalid JSON.") from exc

            for entry in payload.get("data") or []:
                results.append(
                    {
                        "episode_number": entry.get("mal_id"),
                        "title": entry.get("title"),
                        "description": None,
                        "air_date": (entry.get("aired") or "").split("T")[0] or None,
                        "runtime_minutes": None,
                        "still_url": None,
                    }
                )
            has_next = ((payload.get("pagination") or {}).get("has_next_page")) or False
            if not has_next:
                break
            page += 1
        return results
