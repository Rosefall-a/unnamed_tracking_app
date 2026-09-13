from __future__ import annotations

import re
from typing import Any

import requests

_URL = "https://graphql.anilist.co"
_TAG_RE = re.compile(r"<[^>]+>")

_QUERY = """
query ($search: String, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    media(search: $search, type: ANIME) {
      id
      title {
        romaji
        english
      }
      description(asHtml: false)
      startDate {
        year
        month
        day
      }
      episodes
      duration
      studios(isMain: true) {
        nodes {
          name
        }
      }
      countryOfOrigin
      genres
      coverImage {
        extraLarge
        large
      }
      averageScore
      siteUrl
    }
  }
}
"""


class AniListError(RuntimeError):
    """Raised when AniList responds unsuccessfully."""


def _clean_description(value: str | None) -> str | None:
    if not value:
        return None
    return _TAG_RE.sub("", value).strip() or None


def _format_date(start_date: dict[str, Any] | None) -> str | None:
    if not start_date or not start_date.get("year"):
        return None
    year = start_date["year"]
    month = start_date.get("month") or 1
    day = start_date.get("day") or 1
    return f"{year:04d}-{month:02d}-{day:02d}"


class AniListClient:
    """Minimal client for AniList's public GraphQL API. No authentication
    required for read-only search queries — OAuth is only needed to
    mutate a user's own AniList list, which this app never does."""

    def __init__(self, *, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        try:
            response = self.session.post(
                _URL,
                json={"query": _QUERY, "variables": {"search": query, "perPage": limit}},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise AniListError(f"Could not reach AniList: {exc}") from exc
        if response.status_code >= 400:
            raise AniListError(f"AniList request failed ({response.status_code}): {response.text[:200]}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise AniListError("AniList returned invalid JSON.") from exc
        if "errors" in payload:
            messages = "; ".join(e.get("message", "unknown error") for e in payload["errors"])
            raise AniListError(f"AniList returned an error: {messages}")

        media = (payload.get("data") or {}).get("Page", {}).get("media") or []
        results: list[dict[str, Any]] = []
        for entry in media[:limit]:
            title = entry.get("title") or {}
            cover = entry.get("coverImage") or {}
            studios = [n["name"] for n in (entry.get("studios") or {}).get("nodes", []) if n.get("name")]
            score = entry.get("averageScore")
            results.append(
                {
                    "id": entry.get("id"),
                    "title": title.get("english") or title.get("romaji"),
                    "overview": _clean_description(entry.get("description")),
                    "release_date": _format_date(entry.get("startDate")),
                    "episode_runtime_minutes": entry.get("duration"),
                    "episode_count": entry.get("episodes"),
                    "studios": studios,
                    "countries": [entry["countryOfOrigin"]] if entry.get("countryOfOrigin") else [],
                    "genres": entry.get("genres") or [],
                    "poster_url": cover.get("extraLarge") or cover.get("large"),
                    "score": (score / 10) if score is not None else None,
                    "url": entry.get("siteUrl"),
                }
            )
        return results
