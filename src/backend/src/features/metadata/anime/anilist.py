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
      format
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
      bannerImage
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


# AniList's MediaFormat enum -> the friendly label Jikan already returns
# directly, so both providers normalize to the same vocabulary.
_FORMAT_LABELS = {
    "TV": "TV",
    "TV_SHORT": "TV Short",
    "MOVIE": "Movie",
    "SPECIAL": "Special",
    "OVA": "OVA",
    "ONA": "ONA",
    "MUSIC": "Music",
}


def _format_label(raw: str | None) -> str | None:
    if not raw:
        return None
    return _FORMAT_LABELS.get(raw, raw.title())


# AniList's own RelationType enum -> a short human label for the graph
# edge (e.g. "Sequel", "Side story") rather than the raw SCREAMING_SNAKE
# value.
_RELATION_LABELS = {
    "ADAPTATION": "Adaptation",
    "PREQUEL": "Prequel",
    "SEQUEL": "Sequel",
    "PARENT": "Parent story",
    "SIDE_STORY": "Side story",
    "CHARACTER": "Shared character",
    "SUMMARY": "Summary",
    "ALTERNATIVE": "Alternative",
    "SPIN_OFF": "Spin-off",
    "OTHER": "Related",
    "SOURCE": "Source",
    "COMPILATION": "Compilation",
    "CONTAINS": "Contains",
}

_EPISODES_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    episodes
    nextAiringEpisode {
      episode
    }
    streamingEpisodes {
      title
      thumbnail
    }
  }
}
"""

# Same two fields the full episode fetch uses to work out the aired
# total, without the streamingEpisodes list — cheap enough to poll every
# few minutes across a whole library instead of only once a day.
_AIRED_COUNT_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    episodes
    nextAiringEpisode {
      episode
    }
  }
}
"""

# A streaming-episode title usually looks like "Episode 12 - The Real Folk
# Blues" — split off the leading "Episode N" so the stored title matches
# what Jikan would have given us, instead of keeping the number baked in.
_EPISODE_TITLE_RE = re.compile(r"^Episode\s+\d+\s*-\s*(.+)$", re.IGNORECASE)


def _blank_episode(episode_number: int, still_url: str | None = None, title: str | None = None) -> dict[str, Any]:
    return {
        "episode_number": episode_number,
        "title": title,
        "description": None,
        "air_date": None,
        "runtime_minutes": None,
        "still_url": still_url,
    }


def _parse_streaming_episodes(streaming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for i, entry in enumerate(streaming, start=1):
        raw_title = entry.get("title") or ""
        match = _EPISODE_TITLE_RE.match(raw_title)
        title = match.group(1) if match else (raw_title or None)
        results.append(_blank_episode(i, still_url=entry.get("thumbnail"), title=title))
    return results


def _aired_total(media: dict[str, Any]) -> int | None:
    """The real total episode count if known (completed show), otherwise
    how many have aired so far for an ongoing show (nextAiringEpisode's
    number minus one) — AniList only sets `episodes` once a show wraps."""
    next_airing = media.get("nextAiringEpisode")
    if media.get("episodes"):
        return media["episodes"]
    if next_airing and next_airing.get("episode"):
        return next_airing["episode"] - 1
    return None


def _pad_to_aired_total(results: list[dict[str, Any]], aired_total: int | None) -> None:
    """Fill in plain numbered placeholders for every episode number up to
    `aired_total` that streamingEpisodes didn't cover, in place."""
    if not aired_total:
        return
    known = {r["episode_number"] for r in results}
    for n in range(1, aired_total + 1):
        if n not in known:
            results.append(_blank_episode(n))
    results.sort(key=lambda r: r["episode_number"])

_RELATIONS_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    title {
      romaji
      english
    }
    relations {
      edges {
        relationType(version: 2)
        node {
          id
          title {
            romaji
            english
          }
          format
          coverImage {
            extraLarge
            large
          }
        }
      }
    }
    recommendations(sort: RATING_DESC, perPage: 10) {
      nodes {
        mediaRecommendation {
          id
          title {
            romaji
            english
          }
          format
          coverImage {
            extraLarge
            large
          }
        }
      }
    }
  }
}
"""


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
                    "backdrop_url": entry.get("bannerImage"),
                    "score": (score / 10) if score is not None else None,
                    "format": _format_label(entry.get("format")),
                    "url": entry.get("siteUrl"),
                }
            )
        return results

    def episodes(self, anilist_id: str) -> list[dict[str, Any]]:
        """Episode data via AniList's `streamingEpisodes` — thumbnail +
        title only, no air date or synopsis (AniList doesn't track those
        per-episode). Thinner than Jikan's data, but it's a real fallback
        for when Jikan is unreachable, rather than showing nothing.

        `streamingEpisodes` alone is badly incomplete for long-running
        shows (e.g. only the first ~69 of 1000+ One Piece episodes) — for
        an ongoing show AniList's own `episodes` total is null too (there
        is no fixed total yet), so `nextAiringEpisode.episode - 1` is used
        as the real aired-so-far count when present, and the remainder is
        padded as plain numbered placeholders so the full aired run is at
        least trackable even without rich metadata for every episode."""
        try:
            response = self.session.post(
                _URL,
                json={"query": _EPISODES_QUERY, "variables": {"id": int(anilist_id)}},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise AniListError(f"Could not reach AniList: {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise AniListError(f"Invalid AniList id: {anilist_id!r}") from exc
        if response.status_code >= 400:
            raise AniListError(
                f"AniList request failed ({response.status_code}): {response.text[:200]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise AniListError("AniList returned invalid JSON.") from exc
        if "errors" in payload:
            messages = "; ".join(e.get("message", "unknown error") for e in payload["errors"])
            raise AniListError(f"AniList returned an error: {messages}")

        media = (payload.get("data") or {}).get("Media")
        if not media:
            return []

        results = _parse_streaming_episodes(media.get("streamingEpisodes") or [])
        _pad_to_aired_total(results, _aired_total(media))
        return results

    def airing_status(self, anilist_id: str) -> tuple[int | None, bool]:
        """`(aired_episode_count, is_airing)` — the same two fields
        `episodes()` uses to compute a total, without the
        `streamingEpisodes` list, so this is cheap enough to poll every
        few minutes across a whole library to catch a newly-aired
        episode quickly, instead of running the full (thumbnail-fetching,
        TMDB-backfilling) sync on that cadence. `is_airing` is just
        whether AniList still has a `nextAiringEpisode` scheduled."""
        try:
            response = self.session.post(
                _URL,
                json={"query": _AIRED_COUNT_QUERY, "variables": {"id": int(anilist_id)}},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise AniListError(f"Could not reach AniList: {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise AniListError(f"Invalid AniList id: {anilist_id!r}") from exc
        if response.status_code >= 400:
            raise AniListError(
                f"AniList request failed ({response.status_code}): {response.text[:200]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise AniListError("AniList returned invalid JSON.") from exc
        if "errors" in payload:
            messages = "; ".join(e.get("message", "unknown error") for e in payload["errors"])
            raise AniListError(f"AniList returned an error: {messages}")

        media = (payload.get("data") or {}).get("Media")
        if not media:
            return None, False
        next_airing = media.get("nextAiringEpisode")
        is_airing = bool(next_airing and next_airing.get("episode"))
        return _aired_total(media), is_airing

    def relations_and_recommendations(self, title: str) -> dict[str, Any]:
        """One request gets both the real prequel/sequel/spin-off graph
        (relations) and AniList's own recommendation list for the best
        title match — cheaper than two separate lookups, and both tabs
        need the same "find this anime on AniList" step first anyway."""
        if not title.strip():
            return {"relations": [], "recommendations": []}
        try:
            response = self.session.post(
                _URL,
                json={"query": _RELATIONS_QUERY, "variables": {"search": title}},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise AniListError(f"Could not reach AniList: {exc}") from exc
        if response.status_code >= 400:
            raise AniListError(
                f"AniList request failed ({response.status_code}): {response.text[:200]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise AniListError("AniList returned invalid JSON.") from exc
        if "errors" in payload:
            messages = "; ".join(e.get("message", "unknown error") for e in payload["errors"])
            raise AniListError(f"AniList returned an error: {messages}")

        media = (payload.get("data") or {}).get("Media")
        if not media:
            return {"relations": [], "recommendations": []}

        def _node_to_dict(node: dict[str, Any]) -> dict[str, Any]:
            node_title = node.get("title") or {}
            cover = node.get("coverImage") or {}
            return {
                "id": node.get("id"),
                "title": node_title.get("english") or node_title.get("romaji"),
                "format": _format_label(node.get("format")),
                "poster_url": cover.get("extraLarge") or cover.get("large"),
            }

        relations = []
        for edge in (media.get("relations") or {}).get("edges") or []:
            node = edge.get("node")
            if not node:
                continue
            entry = _node_to_dict(node)
            entry["relation_label"] = _RELATION_LABELS.get(
                edge.get("relationType"), "Related"
            )
            relations.append(entry)

        recommendations = []
        for rec in (media.get("recommendations") or {}).get("nodes") or []:
            node = rec.get("mediaRecommendation")
            if not node:
                continue
            recommendations.append(_node_to_dict(node))

        return {"relations": relations, "recommendations": recommendations}
