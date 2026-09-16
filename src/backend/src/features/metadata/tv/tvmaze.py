from __future__ import annotations

import re
from typing import Any

import requests

_BASE_URL = "https://api.tvmaze.com"
_TAG_RE = re.compile(r"<[^>]+>")


class TVMazeError(RuntimeError):
    """Raised when TVmaze responds unsuccessfully."""


class TVMazeClient:
    """TVmaze is a public, keyless TV show database — no API key needed,
    so it always runs alongside TMDB/OMDb rather than being gated by
    AppIntegrationSettings like they are. Runs even when neither TMDB nor
    OMDb is configured, giving TV search a working result out of the box."""

    def __init__(self, *, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        try:
            response = self.session.get(
                f"{_BASE_URL}/search/shows",
                params={"q": query},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise TVMazeError(f"Could not reach TVmaze: {exc}") from exc
        if response.status_code >= 400:
            raise TVMazeError(f"TVmaze request failed ({response.status_code}): {response.text[:200]}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise TVMazeError("TVmaze returned invalid JSON.") from exc

        results: list[dict[str, Any]] = []
        for entry in payload[:limit]:
            show = entry.get("show") or {}
            image = show.get("image") or {}
            network = (show.get("network") or show.get("webChannel") or {}).get("name")
            rating = (show.get("rating") or {}).get("average")
            results.append(
                {
                    "id": show.get("id"),
                    "title": show.get("name") or "",
                    "overview": _TAG_RE.sub("", show.get("summary") or "").strip() or None,
                    "first_air_date": show.get("premiered"),
                    "episode_runtime_minutes": show.get("averageRuntime") or show.get("runtime"),
                    "studios": [network] if network else [],
                    "countries": [],
                    "genres": show.get("genres") or [],
                    "poster_url": image.get("original") or image.get("medium"),
                    "score": rating,
                    "url": show.get("url"),
                }
            )
        return results

    def show_status(self, show_id: str) -> str | None:
        """Just the show's own `status` field ("Running", "Ended", "To
        Be Determined", etc.) — a single small object, not the episode
        list, so the frequent airing-check loop can cheaply tell whether
        a show is even worth fetching episodes for on a given pass."""
        try:
            response = self.session.get(f"{_BASE_URL}/shows/{show_id}", timeout=15)
        except requests.RequestException as exc:
            raise TVMazeError(f"Could not reach TVmaze: {exc}") from exc
        if response.status_code >= 400:
            raise TVMazeError(f"TVmaze request failed ({response.status_code}): {response.text[:200]}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise TVMazeError("TVmaze returned invalid JSON.") from exc
        return payload.get("status")

    def episodes(self, show_id: str) -> list[dict[str, Any]]:
        """Every episode of a show in one call — TVmaze has no per-season
        endpoint, so this is filtered down to one season by the caller."""
        try:
            response = self.session.get(
                f"{_BASE_URL}/shows/{show_id}/episodes",
                timeout=15,
            )
        except requests.RequestException as exc:
            raise TVMazeError(f"Could not reach TVmaze: {exc}") from exc
        if response.status_code >= 400:
            raise TVMazeError(f"TVmaze request failed ({response.status_code}): {response.text[:200]}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise TVMazeError("TVmaze returned invalid JSON.") from exc

        results: list[dict[str, Any]] = []
        for entry in payload:
            image = entry.get("image") or {}
            results.append(
                {
                    "season_number": entry.get("season"),
                    "episode_number": entry.get("number"),
                    "title": entry.get("name"),
                    "description": _TAG_RE.sub("", entry.get("summary") or "").strip() or None,
                    "air_date": entry.get("airdate") or None,
                    "runtime_minutes": entry.get("runtime"),
                    "still_url": image.get("original") or image.get("medium"),
                }
            )
        return results
