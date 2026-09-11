from __future__ import annotations

from typing import Any

import requests

_BASE_URL = "https://api.themoviedb.org/3"
_POSTER_BASE = "https://image.tmdb.org/t/p/w500"


class TMDBError(RuntimeError):
    """Raised when TMDB responds unsuccessfully or the API key is missing."""


class TMDBClient:
    """Minimal client for TMDB v3. One deployment-wide API key (see
    database/models/app_integration_settings.py), no per-user auth."""

    def __init__(self, api_key: str | None, *, session: requests.Session | None = None) -> None:
        if not api_key:
            raise TMDBError("TMDB_API_KEY is not configured on the server.")
        self.api_key = api_key
        self.session = session or requests.Session()

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        try:
            response = self.session.get(
                f"{_BASE_URL}{path}",
                params={**params, "api_key": self.api_key},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise TMDBError(f"Could not reach TMDB: {exc}") from exc
        if response.status_code >= 400:
            raise TMDBError(f"TMDB request failed ({response.status_code}): {response.text[:200]}")
        try:
            return response.json()
        except ValueError as exc:
            raise TMDBError("TMDB returned invalid JSON.") from exc

    def _details(self, movie_id: int) -> dict[str, Any]:
        return self._get(f"/movie/{movie_id}", {"append_to_response": "credits"})

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        payload = self._get("/search/movie", {"query": query})
        candidates = payload.get("results") or []

        results: list[dict[str, Any]] = []
        for candidate in candidates[:limit]:
            movie_id = candidate.get("id")
            if movie_id is None:
                continue
            try:
                details = self._details(movie_id)
            except TMDBError:
                details = candidate

            crew = (details.get("credits") or {}).get("crew") or []
            director = next((c["name"] for c in crew if c.get("job") == "Director"), None)
            writer = next(
                (c["name"] for c in crew if c.get("job") in ("Writer", "Screenplay")), None
            )
            poster_path = details.get("poster_path") or candidate.get("poster_path")

            results.append(
                {
                    "id": movie_id,
                    "title": details.get("title") or candidate.get("title"),
                    "overview": details.get("overview") or candidate.get("overview"),
                    "release_date": details.get("release_date") or candidate.get("release_date"),
                    "runtime_minutes": details.get("runtime"),
                    "director": director,
                    "writer": writer,
                    "studios": [
                        c["name"] for c in details.get("production_companies", []) if c.get("name")
                    ],
                    "countries": [
                        c["name"] for c in details.get("production_countries", []) if c.get("name")
                    ],
                    "languages": [
                        lang["english_name"]
                        for lang in details.get("spoken_languages", [])
                        if lang.get("english_name")
                    ],
                    "genres": [g["name"] for g in details.get("genres", []) if g.get("name")],
                    "poster_url": f"{_POSTER_BASE}{poster_path}" if poster_path else None,
                    "vote_average": details.get("vote_average") or candidate.get("vote_average"),
                    "url": f"https://www.themoviedb.org/movie/{movie_id}",
                }
            )
        return results
