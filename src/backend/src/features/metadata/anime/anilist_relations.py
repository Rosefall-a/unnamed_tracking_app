"""Pure normalization and graph rules for AniList relation payloads."""

from __future__ import annotations

from typing import Any

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


def format_label(raw: str | None) -> str | None:
    if not raw:
        return None
    return _FORMAT_LABELS.get(raw, raw.title())


def node_to_dict(node: dict[str, Any]) -> dict[str, Any]:
    node_title = node.get("title") or {}
    cover = node.get("coverImage") or {}
    return {
        "id": node.get("id"),
        "title": node_title.get("english") or node_title.get("romaji"),
        "format": format_label(node.get("format")),
        "poster_url": cover.get("extraLarge") or cover.get("large"),
        "episode_count": node.get("episodes"),
        "year": (node.get("startDate") or {}).get("year"),
    }


# AniList's own RelationType enum -> a short human label for the graph
# edge (e.g. "Sequel", "Side story") rather than the raw SCREAMING_SNAKE
# value.
RELATION_LABELS = {
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
_MAX_BRANCHES = 40


# Relation types that read as clutter rather than a genuinely related
# title — a shared-character cameo, or a clip-show/recap compilation —
# so they're left out of the graph entirely rather than competing for
# space with the source manga/novel, side stories, and spin-offs that
# actually matter. "Other" is deliberately NOT filtered: AniList uses it
# for real named specials/shorts too (e.g. a movie recap special isn't
# always tagged more specifically), not just noise.

_LOW_VALUE_BRANCH_TYPES = {"CHARACTER"}


_CHAIN_RELATION_TYPES = {"PREQUEL", "SEQUEL"}


def topological_order(ids: set[int], prequel_of: dict[int, int]) -> list[int] | None:
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


def collect_branches(
    nodes: dict[int, dict[str, Any]], anchor_id: int, chain_ids: list[int]
) -> list[dict[str, Any]]:
    """Every relation attached to the anchor entry itself — not every
    entry in the chain — that isn't itself another chain link:
    adaptation, side story, source manga/novel, etc., up to
    `_MAX_BRANCHES` total. Scoped to just the anchor rather than the
    whole chain on purpose: a real prequel/sequel chain can run deep
    (a long-running show easily has 5+ entries), and giving every one
    of them its own branch subtree leaves nowhere collision-free to put
    them — they'd all have to share the same horizontal band the chain
    row itself occupies, and a wide subtree hanging off an early entry
    can reach into a later entry's own position. Low-value relation
    types (shared character, compilation, ...) are skipped so they
    don't clutter the graph with rarely-useful nodes."""
    branches: list[dict[str, Any]] = []
    seen = set(chain_ids)
    edges = (nodes[anchor_id].get("relations") or {}).get("edges") or []
    for edge in edges:
        if len(branches) >= _MAX_BRANCHES:
            break
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
                "anchor_id": anchor_id,
                "anchor_kind": "show",
                "relation_label": RELATION_LABELS.get(rtype, "Related"),
                **node_to_dict(node),
            }
        )
    return branches
