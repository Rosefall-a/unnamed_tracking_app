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


def _node_to_dict(node: dict[str, Any]) -> dict[str, Any]:
    node_title = node.get("title") or {}
    cover = node.get("coverImage") or {}
    return {
        "id": node.get("id"),
        "title": node_title.get("english") or node_title.get("romaji"),
        "format": _format_label(node.get("format")),
        "poster_url": cover.get("extraLarge") or cover.get("large"),
        "episode_count": node.get("episodes"),
        "year": (node.get("startDate") or {}).get("year"),
    }


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
    """How many episodes have actually aired so far. A season can have a
    confirmed total episode count (e.g. 14) while still airing weekly
    (e.g. only 12 out) — `nextAiringEpisode`, when present, is what's
    actually aired and takes priority over the confirmed total. Only
    fall back to `episodes` once AniList reports nothing left scheduled,
    meaning the show has genuinely wrapped."""
    next_airing = media.get("nextAiringEpisode")
    if next_airing and next_airing.get("episode"):
        return next_airing["episode"] - 1
    if media.get("episodes"):
        return media["episodes"]
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
    format
    episodes
    startDate {
      year
    }
    coverImage {
      extraLarge
      large
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
          episodes
          startDate {
            year
          }
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
          episodes
          startDate {
            year
          }
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

# Same shape as _RELATIONS_QUERY but looked up by AniList's own id rather
# than a text search — used while walking the prequel/sequel chain, where
# every step after the first already has a real id to follow instead of
# a title to (re-)search for.
_RELATIONS_BY_ID_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title {
      romaji
      english
    }
    format
    episodes
    startDate {
      year
    }
    coverImage {
      extraLarge
      large
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
          episodes
          startDate {
            year
          }
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
          episodes
          startDate {
            year
          }
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

# How far the chain walk follows PREQUEL/SEQUEL edges in each direction,
# and how many off-chain relations (adaptation, side story, source
# manga/novel, etc.) get surfaced as branches — generous enough for a
# real franchise's full run without risking a runaway request chain.
_MAX_CHAIN_HOPS = 8
_MAX_BRANCHES = 24
_CHAIN_RELATION_TYPES = {"PREQUEL", "SEQUEL"}

# Relation types that read as clutter rather than a genuinely related
# title — a shared-character cameo, a clip-show/recap compilation, or
# AniList's catch-all "other" bucket — so they're left out of the graph
# entirely rather than competing for space with the source manga/novel,
# side stories, and spin-offs that actually matter.
_LOW_VALUE_BRANCH_TYPES = {"CHARACTER", "SUMMARY", "COMPILATION", "CONTAINS", "OTHER"}


def _topological_order(ids: set[int], prequel_of: dict[int, int]) -> list[int] | None:
    """Orders `ids` earliest-prequel-first using each id's prequel
    pointer (only ones pointing within `ids` matter). Returns None if
    the pointers don't fully resolve every id — a partial/cyclic result
    isn't trustworthy enough to reorder anything."""
    if not prequel_of:
        return None
    order: list[int] = []
    remaining = set(ids)
    guard = 0
    while remaining and guard <= len(ids):
        guard += 1
        ready = sorted(i for i in remaining if prequel_of.get(i) not in remaining)
        if not ready:
            break
        order.extend(ready)
        remaining.difference_update(ready)
    return None if remaining else order


def _collect_branches(
    nodes: dict[int, dict[str, Any]], chain_ids: list[int]
) -> list[dict[str, Any]]:
    """Every relation attached to a chain node that isn't itself another
    chain link — adaptation, side story, source manga/novel, etc. — up
    to `_MAX_BRANCHES` total, deduplicated across the whole chain.
    Low-value relation types (shared character, compilation, ...) are
    skipped so they don't clutter the graph with rarely-useful nodes."""
    branches: list[dict[str, Any]] = []
    seen = set(chain_ids)
    for node_id in chain_ids:
        if len(branches) >= _MAX_BRANCHES:
            break
        edges = (nodes[node_id].get("relations") or {}).get("edges") or []
        for edge in edges:
            node = edge.get("node")
            if not node:
                continue
            rtype = edge.get("relationType")
            target_id = node["id"]
            if rtype in _CHAIN_RELATION_TYPES and target_id in nodes:
                continue  # already represented as a chain link
            if rtype in _LOW_VALUE_BRANCH_TYPES:
                continue
            if target_id in seen:
                continue
            seen.add(target_id)
            branches.append(
                {
                    "anchor_id": node_id,
                    "relation_label": _RELATION_LABELS.get(rtype, "Related"),
                    **_node_to_dict(node),
                }
            )
            if len(branches) >= _MAX_BRANCHES:
                break
    return branches


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

    def _fetch_relations_node(
        self, *, media_id: int | None = None, search: str | None = None
    ) -> dict[str, Any] | None:
        """One request's worth of a single Media node: its own id/title
        plus its direct relations edges and recommendations — the unit
        both `relations_and_recommendations` and the chain walk in
        `relations_chain_and_branches` are built from."""
        variables: dict[str, Any]
        if media_id is not None:
            query, variables = _RELATIONS_BY_ID_QUERY, {"id": media_id}
        else:
            query, variables = _RELATIONS_QUERY, {"search": search}
        try:
            response = self.session.post(_URL, json={"query": query, "variables": variables}, timeout=15)
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
        return (payload.get("data") or {}).get("Media")

    def relations_and_recommendations(self, title: str) -> dict[str, Any]:
        """One request gets both the real prequel/sequel/spin-off graph
        (relations) and AniList's own recommendation list for the best
        title match — cheaper than two separate lookups, and both tabs
        need the same "find this anime on AniList" step first anyway."""
        if not title.strip():
            return {"relations": [], "recommendations": []}
        media = self._fetch_relations_node(search=title)
        if not media:
            return {"relations": [], "recommendations": []}

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

    def _walk_chain(
        self, nodes: dict[int, dict[str, Any]], chain_ids: list[int], anchor_id: int
    ) -> None:
        """Extends `chain_ids`/`nodes` in place, following PREQUEL edges
        backward and SEQUEL edges forward from the anchor, up to
        `_MAX_CHAIN_HOPS` each way, guarded against cycles."""

        def _walk_one_direction(relation_type: str, prepend: bool) -> None:
            current_id = anchor_id
            for _ in range(_MAX_CHAIN_HOPS):
                edges = (nodes[current_id].get("relations") or {}).get("edges") or []
                edge = next(
                    (e for e in edges if e.get("relationType") == relation_type), None
                )
                if not edge or not edge.get("node"):
                    break
                next_id = edge["node"]["id"]
                if next_id in nodes:
                    break  # cycle guard — a franchise's edges can loop back
                try:
                    next_node = self._fetch_relations_node(media_id=next_id)
                except AniListError:
                    break  # a flaky/missing hop ends the walk, not the whole tab
                if not next_node:
                    break
                nodes[next_id] = next_node
                if prepend:
                    chain_ids.insert(0, next_id)
                else:
                    chain_ids.append(next_id)
                current_id = next_id

        _walk_one_direction("PREQUEL", prepend=True)
        _walk_one_direction("SEQUEL", prepend=False)

    def relations_chain_and_branches(
        self, title: str, anilist_id: str | None = None
    ) -> dict[str, Any]:
        """The full prequel/sequel chain this entry belongs to — walked
        via PREQUEL/SEQUEL edges in both directions, not just the single
        hop `relations_and_recommendations` returns — plus every other
        relation type (adaptation, side story, source manga/novel, etc.)
        attached to whichever chain entry it's actually connected to.
        A season otherwise only ever lists its immediate neighbor, which
        reads as missing entries for any franchise 3+ seasons deep."""
        anchor = self._fetch_relations_node(
            media_id=int(anilist_id) if anilist_id else None,
            search=None if anilist_id else title,
        )
        if not anchor:
            return {"chain": [], "branches": [], "recommendations": []}

        nodes: dict[int, dict[str, Any]] = {anchor["id"]: anchor}
        chain_ids: list[int] = [anchor["id"]]
        self._walk_chain(nodes, chain_ids, anchor["id"])

        chain = []
        for node_id in chain_ids:
            entry = _node_to_dict(nodes[node_id])
            entry["is_current"] = node_id == anchor["id"]
            chain.append(entry)

        recommendations = []
        for rec in (anchor.get("recommendations") or {}).get("nodes") or []:
            node = rec.get("mediaRecommendation")
            if not node:
                continue
            recommendations.append(_node_to_dict(node))

        return {
            "chain": chain,
            "branches": self._order_related_branches(_collect_branches(nodes, chain_ids)),
            "recommendations": recommendations,
        }

    def _fetch_group_prequel_pointers(
        self, group: list[dict[str, Any]], ids: set[int]
    ) -> dict[int, int]:
        """Fetches each group member's own relations and returns
        {member_id: its_prequel_id} restricted to prequels that are
        themselves in the group (an outside prequel isn't useful for
        ordering the group)."""
        prequel_of: dict[int, int] = {}
        for b in group:
            try:
                node = self._fetch_relations_node(media_id=b["id"])
            except AniListError:
                continue  # one flaky/missing member shouldn't sink the whole tab
            if not node:
                continue
            for edge in (node.get("relations") or {}).get("edges") or []:
                if edge.get("relationType") != "PREQUEL":
                    continue
                target = (edge.get("node") or {}).get("id")
                if isinstance(target, int) and target in ids:
                    prequel_of[b["id"]] = target
        return prequel_of

    def _order_related_branches(
        self, branches: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """A branch group sharing the same anchor and relation label —
        e.g. a two-part movie duology, both tagged ALTERNATIVE to the
        parent show rather than SEQUEL/PREQUEL to it — can still be
        chronologically ordered relative to each other via their own
        mutual PREQUEL edges. Fetches each 2+-member group once to find
        that order instead of leaving the pieces in arbitrary API order."""
        groups: dict[tuple[int, str], list[int]] = {}
        for i, b in enumerate(branches):
            groups.setdefault((b["anchor_id"], b["relation_label"]), []).append(i)

        for positions in groups.values():
            if len(positions) < 2:
                continue
            group = [branches[i] for i in positions]
            ids = {b["id"] for b in group}
            prequel_of = self._fetch_group_prequel_pointers(group, ids)
            order = _topological_order(ids, prequel_of)
            if order is None:
                continue  # couldn't fully resolve — leave original order
            by_id = {b["id"]: b for b in group}
            for slot, branch_id in zip(sorted(positions), order):
                branches[slot] = by_id[branch_id]
        return branches
