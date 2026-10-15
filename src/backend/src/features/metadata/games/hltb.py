from __future__ import annotations

import re
import time
from typing import Any

import requests

# HowLongToBeat answers 403 to anything that does not look like a browser (the
# previous "compatible; unnamed-tracking-app" agent was refused on every page). A
# plain desktop browser agent is accepted.
_BROWSER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_SITE = "https://howlongtobeat.com"

# the site's four figures, in seconds, and the game field each one fills
_TIME_FIELDS = {
    "time_to_beat_hours": "comp_main",  # main story
    "time_to_beat_extras_hours": "comp_plus",  # main story and extras
    "time_to_beat_completionist_hours": "comp_100",  # everything, 100%
    "time_to_beat_all_hours": "comp_all",  # average over all play styles
}


def _hours(seconds: Any) -> float | None:
    return round(seconds / 3600, 1) if isinstance(seconds, (int, float)) and seconds > 0 else None


class HLTBError(RuntimeError):
    """Raised when HowLongToBeat's unofficial search endpoint is unreachable
    or returns something unexpected."""


class HLTBClient:
    """HowLongToBeat has no official API — this hits the same unofficial
    search the site's own page uses: ask `/api/search/site/init` for a short-lived
    token (tied to this address and browser agent), then post the search with it in
    `x-auth-token`. No key is needed. The token is renewed once when the site says it
    expired (403). If searches start failing site-wide, the site changed that
    handshake again; the page's own script (`/_next/static/chunks`) shows the new one."""

    INIT_URL = f"{_SITE}/api/search/site/init"
    SEARCH_URL = f"{_SITE}/api/search/site"

    def __init__(self, *, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        # assigned, not defaulted: a session already carries "python-requests" as its
        # agent, which a default would leave in place
        self.session.headers.update(
            {
                "User-Agent": _BROWSER_AGENT,
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": f"{_SITE}/",
                "Origin": _SITE,
            }
        )
        self._token: str | None = None
        self._visited = False

    def _fetch_token(self) -> str:
        try:
            if not self._visited:
                # the site hands out its cookie on the first page; the token request
                # is refused without it
                self.session.get(f"{_SITE}/", timeout=6)
                self._visited = True
            response = self.session.get(
                self.INIT_URL, params={"t": int(time.time() * 1000)}, timeout=6
            )
        except requests.RequestException as exc:
            raise HLTBError(f"Could not reach HowLongToBeat: {exc}") from exc
        if response.status_code >= 400:
            raise HLTBError(f"HowLongToBeat refused the request ({response.status_code}).")
        try:
            token = response.json().get("token")
        except ValueError as exc:
            raise HLTBError("HowLongToBeat returned invalid JSON.") from exc
        if not token:
            raise HLTBError("HowLongToBeat gave no search token.")
        self._token = token
        return token

    def search(self, title: str, limit: int = 5) -> list[dict[str, Any]]:
        if not title.strip():
            return []

        terms = re.sub(r"[^\w\s]", " ", title).split()
        if not terms:
            return []
        body = {
            "searchType": "games",
            "searchTerms": terms,
            "searchPage": 1,
            "size": limit,
            "searchOptions": {
                "games": {
                    "userId": 0,
                    "platform": "",
                    "sortCategory": "popular",
                    "rangeCategory": "main",
                    "rangeTime": {"min": None, "max": None},
                    "gameplay": {"perspective": "", "flow": "", "genre": "", "difficulty": ""},
                    "rangeYear": {"min": "", "max": ""},
                    "modifier": "",
                },
                "users": {"sortCategory": "postcount"},
                "lists": {"sortCategory": "follows"},
                "filter": "",
                "sort": 0,
                "randomizer": 0,
            },
            "useCache": True,
        }

        # short timeouts — the caller (search.py) also enforces its own hard
        # wall-clock cap in case a stalled connection doesn't respect them
        response = None
        for attempt in range(2):
            token = self._token or self._fetch_token()
            try:
                response = self.session.post(
                    self.SEARCH_URL, json=body, headers={"x-auth-token": token}, timeout=6
                )
            except requests.RequestException as exc:
                raise HLTBError(f"Could not reach HowLongToBeat: {exc}") from exc
            if response.status_code == 403 and attempt == 0:
                # the token ran out: get a new one and ask once more
                self._token = None
                continue
            break

        if response is None or response.status_code >= 400:
            code = response.status_code if response is not None else "no answer"
            raise HLTBError(f"HowLongToBeat search failed ({code}).")

        try:
            payload = response.json()
        except ValueError as exc:
            raise HLTBError("HowLongToBeat returned invalid JSON.") from exc

        entries = payload.get("data") or []
        results: list[dict[str, Any]] = []
        for entry in entries:
            results.append(
                {
                    "id": entry.get("game_id"),
                    "title": entry.get("game_name"),
                    **{field: _hours(entry.get(key)) for field, key in _TIME_FIELDS.items()},
                }
            )
        return results

    def find_times(self, title: str) -> dict[str, float]:
        """Every figure the site has for the entry whose name is the title, else for the
        first entry that has any (the site lists the best match first). Keys are the
        game field names; a figure the site has no data for is left out."""
        squash = lambda s: "".join(ch.lower() for ch in str(s or "") if ch.isalnum())  # noqa: E731
        found = [
            r
            for r in self.search(title, limit=5)
            if any(r.get(field) is not None for field in _TIME_FIELDS)
        ]
        chosen = next((r for r in found if squash(r.get("title")) == squash(title)), None)
        chosen = chosen or (found[0] if found else None)
        if chosen is None:
            return {}
        return {field: chosen[field] for field in _TIME_FIELDS if chosen.get(field) is not None}

    def find_time_to_beat(self, title: str) -> float | None:
        """Hours for the main story alone."""
        return self.find_times(title).get("time_to_beat_hours")
