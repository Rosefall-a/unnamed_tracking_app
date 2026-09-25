"""Import a user's public AniList anime list into the local anime library.

This deliberately uses AniList's public MediaListCollection query rather than
OAuth: public lists can be read without credentials, and the importer never
writes back to AniList.
"""

from __future__ import annotations

from typing import Any

from .anilist import AniListClient, AniListError

_LIST_QUERY = """
query ($userName: String!, $chunk: Int!, $perChunk: Int!) {
  MediaListCollection(
    userName: $userName
    type: ANIME
    chunk: $chunk
    perChunk: $perChunk
  ) {
    lists {
      name
      entries {
        id
        status
        score(format: POINT_10)
        progress
        repeat
        priority
        notes
        startedAt {
          year
          month
          day
        }
        completedAt {
          year
          month
          day
        }
        updatedAt
        media {
          id
          title {
            english
            romaji
          }
          description(asHtml: false)
          startDate {
            year
            month
            day
          }
          episodes
          duration
          format
          genres
          countryOfOrigin
          studios(isMain: true) {
            nodes {
              name
            }
          }
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
  }
}
"""

_STATUS_MAP = {
    "CURRENT": "IN_PROGRESS",
    "COMPLETED": "WATCHED",
    "DROPPED": "DROPPED",
    "PAUSED": "BACKLOG",
    "REPEATING": "REWATCH",
    "PLANNING": "WISHLIST",
}

_PRIORITY_MAP = {
    1: "HIGH",
    2: "MEDIUM",
    3: "LOW",
}


def _fuzzy_date(value: dict[str, Any] | None) -> str | None:
    if not value or not value.get("year"):
        return None
    return f"{value['year']:04d}-{value.get('month') or 1:02d}-{value.get('day') or 1:02d}"


def _map_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    media = entry.get("media") or {}
    media_id = media.get("id")
    if not media_id:
        return None

    title_data = media.get("title") or {}
    title = title_data.get("english") or title_data.get("romaji")
    if not title:
        return None

    studios = [
        node["name"] for node in (media.get("studios") or {}).get("nodes", []) if node.get("name")
    ]
    score = entry.get("score")
    average_score = media.get("averageScore")
    entry_status = entry.get("status")
    entry_priority = entry.get("priority")
    return {
        "anilist_id": str(media_id),
        "title": title,
        "description": media.get("description"),
        "first_air_date": _fuzzy_date(media.get("startDate")),
        "episode_runtime_minutes": media.get("duration"),
        "studios": studios,
        "countries": [media["countryOfOrigin"]] if media.get("countryOfOrigin") else [],
        "genres": media.get("genres") or [],
        "format": media.get("format"),
        "anilist_score": average_score / 10 if isinstance(average_score, (int, float)) else None,
        "poster_url": (media.get("coverImage") or {}).get("extraLarge")
        or (media.get("coverImage") or {}).get("large"),
        "backdrop_url": media.get("bannerImage"),
        "site_url": media.get("siteUrl"),
        "status": _STATUS_MAP.get(entry_status, "WISHLIST")
        if isinstance(entry_status, str)
        else "WISHLIST",
        "priority": _PRIORITY_MAP.get(entry_priority) if isinstance(entry_priority, int) else None,
        "rating_overall": score if score not in (None, 0) else None,
        "progress": max(0, int(entry.get("progress") or 0)),
        "repeat": max(0, int(entry.get("repeat") or 0)),
        "note": entry.get("notes") or None,
        "start_date": _fuzzy_date(entry.get("startedAt")),
        "end_date": _fuzzy_date(entry.get("completedAt")),
        "episode_count": media.get("episodes"),
    }


class AniListImportClient(AniListClient):
    """Read public anime list entries for one AniList username."""

    def fetch_user_anime(self, username: str) -> list[dict[str, Any]]:
        """Fetch and normalize every anime entry from a public AniList list."""
        username = username.strip()
        if not username:
            raise AniListError("AniList username is required.")

        entries_by_media_id: dict[int, dict[str, Any]] = {}
        chunk = 1
        per_chunk = 500

        while True:
            payload = self._post_graphql(
                _LIST_QUERY,
                {"userName": username, "chunk": chunk, "perChunk": per_chunk},
            )
            collection = (payload.get("data") or {}).get("MediaListCollection")
            if collection is None:
                raise AniListError("AniList could not find a public anime list for that username.")

            raw_entries = [
                entry
                for media_list in collection.get("lists") or []
                for entry in media_list.get("entries") or []
            ]
            for entry in raw_entries:
                mapped = _map_entry(entry)
                if mapped is None:
                    continue
                media_id = int(mapped["anilist_id"])
                existing = entries_by_media_id.get(media_id)
                if existing is None or (entry.get("updatedAt") or 0) > (
                    existing.get("_updated_at") or 0
                ):
                    mapped["_updated_at"] = entry.get("updatedAt") or 0
                    entries_by_media_id[media_id] = mapped

            # AniList returns fewer entries than requested on the final
            # chunk. Empty lists also mean there is nothing left to import.
            if len(raw_entries) < per_chunk:
                break
            chunk += 1

        for entry in entries_by_media_id.values():
            entry.pop("_updated_at", None)
        return list(entries_by_media_id.values())
