from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

import requests

_BASE_URL = "https://www.omdbapi.com/"
_RUNTIME_RE = re.compile(r"(\d+)")


class OMDBError(RuntimeError):
    """Raised when OMDb responds unsuccessfully or the API key is missing."""


def _parse_runtime(value: str | None) -> int | None:
    if not value:
        return None
    match = _RUNTIME_RE.search(value)
    return int(match.group(1)) if match else None


def _parse_list(value: str | None) -> list[str]:
    if not value or value == "N/A":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _clean(value: str | None) -> str | None:
    return None if not value or value == "N/A" else value


def _parse_date(value: str | None) -> str | None:
    """OMDb's "Released" field reads like "16 Jul 2010" — convert to
    ISO (YYYY-MM-DD) since that's what the rest of the app stores/expects."""
    cleaned = _clean(value)
    if not cleaned:
        return None
    try:
        return datetime.strptime(cleaned, "%d %b %Y").date().isoformat()
    except ValueError:
        return None


def _exact_first(candidates: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Candidates named exactly what was searched for go first, in OMDb's own
    order (best known first), so "Resident Evil" lists the films called that
    before fan videos and spin-offs with longer names."""
    wanted = _plain(query)
    exact = [c for c in candidates if _plain(c.get("Title") or "") == wanted]
    return exact + [c for c in candidates if _plain(c.get("Title") or "") != wanted]


def _plain(text: str) -> str:
    return "".join(ch.lower() for ch in text if ch.isalnum())


class OMDBClient:
    """Minimal client for the OMDb API (IMDb-backed movie data). One
    deployment-wide API key (see database/models/app_integration_settings.py),
    no per-user auth."""

    def __init__(self, api_key: str | None, *, session: requests.Session | None = None) -> None:
        if not api_key:
            raise OMDBError("OMDB_API_KEY is not configured on the server.")
        self.api_key = api_key
        self.session = session or requests.Session()

    def _get(self, params: dict[str, str]) -> dict[str, Any]:
        try:
            response = self.session.get(
                _BASE_URL, params={**params, "apikey": self.api_key}, timeout=15
            )
        except requests.RequestException as exc:
            raise OMDBError(f"Could not reach OMDb: {exc}") from exc
        if response.status_code >= 400:
            raise OMDBError(f"OMDb request failed ({response.status_code}): {response.text[:200]}")
        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise OMDBError("OMDb returned invalid JSON.") from exc
        if payload.get("Response") == "False":
            raise OMDBError(payload.get("Error", "OMDb returned no results."))
        return payload

    def lookup(self, title: str, year: int | None, kind: str) -> dict[str, Any] | None:
        """One exact title (and year) lookup, for importing a list: a single
        request, no candidate list. `kind` is "movie" or "tv". None when OMDb
        does not know the title. OMDb has no season list, so `seasons` is
        always empty."""
        params = {"t": title, "type": "movie" if kind == "movie" else "series"}
        if year:
            params["y"] = str(year)
        try:
            d = self._get(params)
        except OMDBError as exc:
            if "not found" in str(exc).lower():
                return None
            raise
        rating = _clean(d.get("imdbRating"))
        released = _parse_date(d.get("Released"))
        return {
            "overview": _clean(d.get("Plot")),
            "release_date": released,
            "first_air_date": released,
            "runtime_minutes": _parse_runtime(d.get("Runtime")),
            "episode_runtime_minutes": _parse_runtime(d.get("Runtime")),
            "director": _clean(d.get("Director")),
            "writer": _clean(d.get("Writer")),
            "creators": [],
            "studios": [],
            "countries": _parse_list(d.get("Country")),
            "languages": _parse_list(d.get("Language")),
            "genres": _parse_list(d.get("Genre")),
            "poster_url": _clean(d.get("Poster")),
            "vote_average": float(rating) if rating else None,
            "seasons": [],
        }

    def _candidates(self, query: str, kind: str, year: int | None) -> list[dict[str, Any]]:
        """What a search finds. A short title such as "F1" matches so much that
        OMDb refuses the search ("Too many results."), so that one is asked for
        by its exact title instead, which works at any length. The exact answer
        is already the full record, so it needs no second request."""
        params = {"s": query, "type": kind}
        if year:
            params["y"] = str(year)
        try:
            found = self._get(params).get("Search") or []
            # OMDb lists the older films of a name first, so a new or upcoming
            # one ("Resident Evil", 2026) can be missing from a search with no
            # year. Ask for that exact name from this year and next as well:
            # two small requests, and only what really has that name is added.
            if not year:
                seen = {c.get("imdbID") for c in found}
                for recent in self._recent_exact(query, kind):
                    if recent.get("imdbID") not in seen:
                        found.append(recent)
            return found
        except OMDBError as exc:
            message = str(exc).lower()
            # "Movie not found!" is OMDb's normal zero-results response, not
            # a real failure — swallow only that one message so it reads as
            # an empty search instead of a scary error. Anything else (bad
            # key, rate limit, ...) propagates so the caller can surface it.
            if "not found" in message:
                return []
            if "too many results" not in message:
                raise
        exact = {"t": query, "type": kind}
        if year:
            exact["y"] = str(year)
        try:
            return [self._get(exact)]
        except OMDBError as exc:
            if "not found" in str(exc).lower():
                return []
            raise

    def _recent_exact(self, query: str, kind: str) -> list[dict[str, Any]]:
        this_year = date.today().year
        found = []
        for year in (this_year + 1, this_year):
            try:
                found.append(self._get({"t": query, "type": kind, "y": str(year)}))
            except OMDBError:
                # not found, or OMDb is busy: the search itself still stands
                continue
        return found

    def search(
        self, query: str, limit: int = 8, light: bool = False, year: int | None = None
    ) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        candidates = self._candidates(query, "movie", year)

        results: list[dict[str, Any]] = []
        for candidate in _exact_first(candidates, query)[:limit]:
            imdb_id = candidate.get("imdbID")
            if not imdb_id:
                continue
            try:
                full = light or "Plot" in candidate
                details = candidate if full else self._get({"i": imdb_id})
            except OMDBError:
                details = candidate

            imdb_rating = _clean(details.get("imdbRating"))
            poster = _clean(details.get("Poster"))
            results.append(
                {
                    "id": imdb_id,
                    "title": _clean(details.get("Title")) or candidate.get("Title"),
                    "overview": _clean(details.get("Plot")),
                    "release_date": _parse_date(details.get("Released")),
                    # the search answer has the year even when there is no full date
                    "year": (candidate.get("Year") or "")[:4] or None,
                    "runtime_minutes": _parse_runtime(details.get("Runtime")),
                    "director": _clean(details.get("Director")),
                    "writer": _clean(details.get("Writer")),
                    "studios": [],
                    "countries": _parse_list(details.get("Country")),
                    "languages": _parse_list(details.get("Language")),
                    "genres": _parse_list(details.get("Genre")),
                    "poster_url": poster,
                    "vote_average": float(imdb_rating) if imdb_rating else None,
                    "url": f"https://www.imdb.com/title/{imdb_id}/",
                }
            )
        return results

    def search_tv(
        self, query: str, limit: int = 8, light: bool = False, year: int | None = None
    ) -> list[dict[str, Any]]:
        """Like `search`, but for series. OMDb's `totalSeasons` gives a
        count only — no per-season episode counts or air dates, unlike
        TMDB's `seasons` array, so this never contributes a season list."""
        if not query.strip():
            return []
        candidates = self._candidates(query, "series", year)

        results: list[dict[str, Any]] = []
        for candidate in _exact_first(candidates, query)[:limit]:
            imdb_id = candidate.get("imdbID")
            if not imdb_id:
                continue
            try:
                full = light or "Plot" in candidate
                details = candidate if full else self._get({"i": imdb_id})
            except OMDBError:
                details = candidate

            imdb_rating = _clean(details.get("imdbRating"))
            poster = _clean(details.get("Poster"))
            results.append(
                {
                    "id": imdb_id,
                    "title": _clean(details.get("Title")) or candidate.get("Title"),
                    "overview": _clean(details.get("Plot")),
                    "first_air_date": _parse_date(details.get("Released")),
                    # the search answer has the year even when there is no full date
                    "year": (candidate.get("Year") or "")[:4] or None,
                    "episode_runtime_minutes": _parse_runtime(details.get("Runtime")),
                    "creators": _parse_list(details.get("Writer")),
                    "studios": [],
                    "countries": _parse_list(details.get("Country")),
                    "languages": _parse_list(details.get("Language")),
                    "genres": _parse_list(details.get("Genre")),
                    "poster_url": poster,
                    "vote_average": float(imdb_rating) if imdb_rating else None,
                    "seasons": [],
                    "url": f"https://www.imdb.com/title/{imdb_id}/",
                }
            )
        return results
