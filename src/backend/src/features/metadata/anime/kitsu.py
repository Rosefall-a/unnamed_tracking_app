from __future__ import annotations

from typing import Any

import requests

_BASE_URL = "https://kitsu.io/api/edge"
_EPISODE_PAGE_SIZE = 20


class KitsuError(RuntimeError):
    """Raised when Kitsu responds unsuccessfully."""


def _normalize_title(title: str) -> str:
    return " ".join(title.strip().lower().split())


class KitsuClient:
    """Minimal client for Kitsu's public, keyless JSON:API — the third
    episode-data source alongside Jikan and AniList. Kitsu's own episode
    endpoint carries a real per-episode thumbnail (Jikan has none at
    all) plus a synopsis and air date, so it's a genuine third chance to
    fill in whatever the other two are still missing, not just a
    duplicate of one of them."""

    def __init__(self, *, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def find_exact(self, title: str) -> str | None:
        """Searches by title and returns the id only when a result's own
        title matches exactly (case/whitespace-insensitive) — the same
        safety net `_find_by_exact_title` uses for AniList, so a search
        miss never silently attaches episode data from an unrelated
        show. Checks both the canonical title and any alternate titles
        Kitsu lists, since its canonical title is sometimes the Japanese
        romaji rather than the English name this app stores."""
        try:
            response = self.session.get(
                f"{_BASE_URL}/anime",
                params={"filter[text]": title, "page[limit]": "5"},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise KitsuError(f"Could not reach Kitsu: {exc}") from exc
        if response.status_code >= 400:
            raise KitsuError(f"Kitsu request failed ({response.status_code}): {response.text[:200]}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise KitsuError("Kitsu returned invalid JSON.") from exc

        target = _normalize_title(title)
        for entry in payload.get("data") or []:
            attrs = entry.get("attributes") or {}
            candidates = [attrs.get("canonicalTitle")] + list((attrs.get("titles") or {}).values())
            if any(c and _normalize_title(c) == target for c in candidates):
                return str(entry["id"])
        return None

    def episodes(self, kitsu_id: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        offset = 0
        while True:
            try:
                response = self.session.get(
                    f"{_BASE_URL}/anime/{kitsu_id}/episodes",
                    params={"page[limit]": str(_EPISODE_PAGE_SIZE), "page[offset]": str(offset)},
                    timeout=15,
                )
            except requests.RequestException as exc:
                raise KitsuError(f"Could not reach Kitsu: {exc}") from exc
            if response.status_code >= 400:
                raise KitsuError(
                    f"Kitsu request failed ({response.status_code}): {response.text[:200]}"
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise KitsuError("Kitsu returned invalid JSON.") from exc

            entries = payload.get("data") or []
            for entry in entries:
                attrs = entry.get("attributes") or {}
                number = attrs.get("number")
                if number is None:
                    continue
                thumb = attrs.get("thumbnail") or {}
                results.append(
                    {
                        "episode_number": number,
                        "title": attrs.get("canonicalTitle"),
                        "description": attrs.get("synopsis") or None,
                        "air_date": attrs.get("airdate"),
                        "runtime_minutes": attrs.get("length"),
                        "still_url": thumb.get("original"),
                    }
                )
            if len(entries) < _EPISODE_PAGE_SIZE:
                break
            offset += _EPISODE_PAGE_SIZE
            if offset > 2000:
                break  # matches this codebase's other generous-but-bounded sync caps
        return results
