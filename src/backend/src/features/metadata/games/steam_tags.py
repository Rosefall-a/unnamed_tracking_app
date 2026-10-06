"""Genre tags for a game from the tags Steam's own players give it.

Steam's official genres are broad (Elden Ring is just "Action" and "RPG"), but
its store page also lists the tags players vote on, ranked by votes: Souls-like,
Open World, Dark Fantasy, RPG, Difficult, Action RPG and so on. Those describe a
game far better. The same list is full of things that are not genres
(Singleplayer, Co-op, Controller, Great Soundtrack), which are dropped here.

The tags come from the public store page, the only place Steam shows them.
"""

import json
import re
import threading
import time
from typing import Any

import requests

STORE_URL = "https://store.steampowered.com/app/{app_id}/"
# how many player tags to keep before the official genres are added
MAX_TAGS = 12
# below this many votes on the top tag, players have not tagged the game enough
# to trust, so only the official genres are used
MIN_TOP_VOTES = 20

# Tags that describe how a game is played or built rather than what it is.
# Matched in lowercase against the whole tag.
NON_GENRE_TAGS = frozenset(
    {
        # who plays it
        "singleplayer",
        "multiplayer",
        "co-op",
        "pvp",
        "pve",
        "split screen",
        "massively multiplayer",
        "online pvp",
        "local multiplayer",
        "cross-platform multiplayer",
        # how it is controlled and where it runs
        "controller",
        "vr",
        "vr only",
        "steam deck",
        "remote play",
        "mouse only",
        "touch friendly",
        "gamepad",
        "keyboard",
        # what Steam adds around it
        "steam achievements",
        "steam cloud",
        "steam trading cards",
        "steam workshop",
        "includes level editor",
        "moddable",
        "mod",
        "workshop",
        "early access",
        "free to play",
        "demo",
        "software",
        "utilities",
        "game development",
        # opinions, not descriptions
        "great soundtrack",
        "good soundtrack",
        "soundtrack",
        "beautiful",
        "masterpiece",
        "replay value",
        "relaxing",
        "funny",
        "cute",
        # content warnings and ratings
        "violent",
        "gore",
        "blood",
        "nudity",
        "sexual content",
        "mature",
        "family friendly",
        "kids",
        # how it looks
        "2d",
        "3d",
    }
)
# any tag containing one of these is dropped too (Online Co-Op, Local Co-Op,
# Co-op Campaign, Full controller support, Local Multiplayer ...)
_NON_GENRE_PARTS = ("co-op", "coop", "controller", "multiplayer")

_TAG_MODAL = re.compile(r"InitAppTagModal\(\s*\d+,\s*(\[.*?\]),\s*\[", re.S)

# the store page asks for an age before showing a mature game; these answer it
_STORE_COOKIES = {
    "birthtime": "631152001",
    "lastagecheckage": "1-January-1990",
    "wants_mature_content": "1",
}
_STORE_MIN_GAP = 1.0  # seconds between page requests, to stay polite
_store_lock = threading.Lock()
_store_clock = {"last_request": 0.0}
_store_session = requests.Session()
_store_session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; SteamDataFetcher/1.0)"})


def is_genre_tag(name: str) -> bool:
    """False for the tags that describe modes, controls, features or opinions."""
    lowered = name.strip().lower()
    if not lowered or lowered in NON_GENRE_TAGS:
        return False
    return not any(part in lowered for part in _NON_GENRE_PARTS)


def parse_tags(html: str) -> list[tuple[str, int]]:
    """The (tag, votes) pairs on a store page, most voted first."""
    match = _TAG_MODAL.search(html)
    if not match:
        return []
    try:
        raw = json.loads(match.group(1))
    except ValueError:
        return []
    tags: list[tuple[str, int]] = []
    for entry in raw:
        name = entry.get("name") if isinstance(entry, dict) else None
        if isinstance(name, str) and name.strip():
            votes = entry.get("count")
            tags.append((name.strip(), votes if isinstance(votes, int) else 0))
    return sorted(tags, key=lambda tag: -tag[1])


def pick_genre_tags(player_tags: list[tuple[str, int]], official_genres: list[str]) -> list[str]:
    """The player tags that are genres, most voted first, then any official Steam
    genre they did not already include. A game players have barely tagged keeps
    just its official genres."""
    chosen: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        key = name.strip().lower()
        if key and key not in seen:
            seen.add(key)
            chosen.append(name.strip())

    if player_tags and player_tags[0][1] >= MIN_TOP_VOTES:
        kept = [name for name, _ in player_tags if is_genre_tag(name)]
        for name in kept[:MAX_TAGS]:
            add(name)
    for name in official_genres:
        add(name)
    return chosen


def fetch_player_tags(app_id: int) -> list[tuple[str, int]]:
    """The tags players have given a game, from its store page. Empty when the
    page cannot be read; the tags are an extra, not worth failing a sync over."""
    try:
        with _store_lock:
            wait = _STORE_MIN_GAP - (time.monotonic() - _store_clock["last_request"])
            if wait > 0:
                time.sleep(wait)
            _store_clock["last_request"] = time.monotonic()
            response = _store_session.get(
                STORE_URL.format(app_id=app_id),
                params={"l": "english"},
                cookies=_STORE_COOKIES,
                timeout=20,
            )
        if response.status_code >= 400 or len(response.content) > 5_000_000:
            return []
        return parse_tags(response.text)
    except requests.RequestException:
        return []


def tags_with_player_votes(app_id: int, official_genres: list[str]) -> list[str]:
    """A game's best player tags plus its official genres, or just the official
    genres when the store page could not be read."""
    player_tags = fetch_player_tags(app_id)
    return pick_genre_tags(player_tags, official_genres) if player_tags else official_genres


def official_genre_names(details: dict[str, Any] | None) -> list[str]:
    """Steam's own genres from an app details response."""
    return [g["description"] for g in (details or {}).get("genres", []) if g.get("description")]
