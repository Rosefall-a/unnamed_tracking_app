from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Literal

from src.features.metadata.movies.omdb import OMDBClient
from src.features.metadata.movies.tmdb import TMDBClient
from src.features.metadata.tv.tvmaze import TVMazeClient

# Reuses the TMDB/OMDb clients built for Movies (same API keys, same
# deployment-wide AppIntegrationSettings) rather than duplicating a whole
# second pair of client classes — only the query shape (search_tv vs
# search) and the result field set actually differ.


def _blank_result(provider: str, provider_id: str, title: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "provider_id": provider_id,
        "title": title,
        "description": None,
        "first_air_date": None,
        "episode_runtime_minutes": None,
        "creators": [],
        "studios": [],
        "countries": [],
        "languages": [],
        "genres": [],
        "poster_url": None,
        "backdrop_url": None,
        "tmdb_score": None,
        "seasons": [],
        "url": None,
    }


def _friendly_provider_error(name: str, message: str) -> str:
    lowered = message.lower()
    if "429" in message or "rate limit" in lowered or "too many requests" in lowered:
        return f"{name}: rate limited by the provider, try again in a few minutes."
    return f"{name}: {message}"


def _titles_match(a: str, b: str) -> bool:
    normalize = lambda s: "".join(ch.lower() for ch in s if ch.isalnum())  # noqa: E731
    return normalize(a) == normalize(b) and bool(normalize(a))


def _merge_or_append(results: list[dict[str, Any]], candidate: dict[str, Any]) -> None:
    """A later provider can turn up a title an earlier one already found —
    merge onto the existing entry (filling only blanks) instead of creating
    a visually duplicate second result. `seasons` is never merged: TMDB's
    season list is treated as authoritative when present, never mixed
    with a different provider's (which never has one anyway — see
    OMDBClient.search_tv)."""
    for existing in results:
        if _titles_match(existing["title"], candidate["title"]):
            for key, value in candidate.items():
                if key in ("provider", "provider_id", "title", "seasons"):
                    continue
                if not existing.get(key) and value:
                    existing[key] = value
            return
    results.append(candidate)


@dataclass
class ProviderContext:
    tmdb_api_key: str | None
    omdb_api_key: str | None


ProviderRun = Callable[[str, int, ProviderContext], list[dict[str, Any]]]


@dataclass
class ProviderSpec:
    name: str
    kind: Literal["primary"]
    available: Callable[[ProviderContext], bool]
    run: ProviderRun


def _run_tmdb(query: str, limit: int, ctx: ProviderContext) -> list[dict[str, Any]]:
    assert ctx.tmdb_api_key  # guarded by `available`
    client = TMDBClient(api_key=ctx.tmdb_api_key)
    found: list[dict[str, Any]] = []
    for show in client.search_tv(query, limit=limit):
        result = _blank_result("TMDB", str(show.get("id", "")), show.get("title", ""))
        result.update(
            {
                "description": show.get("overview"),
                "first_air_date": show.get("first_air_date") or None,
                "episode_runtime_minutes": show.get("episode_runtime_minutes"),
                "creators": show.get("creators") or [],
                "studios": show.get("studios") or [],
                "countries": show.get("countries") or [],
                "languages": show.get("languages") or [],
                "genres": show.get("genres") or [],
                "poster_url": show.get("poster_url"),
                "backdrop_url": show.get("backdrop_url"),
                "tmdb_score": show.get("vote_average"),
                "seasons": show.get("seasons") or [],
                "url": show.get("url"),
            }
        )
        found.append(result)
    return found


def _run_omdb(query: str, limit: int, ctx: ProviderContext) -> list[dict[str, Any]]:
    assert ctx.omdb_api_key  # guarded by `available`
    client = OMDBClient(api_key=ctx.omdb_api_key)
    found: list[dict[str, Any]] = []
    for show in client.search_tv(query, limit=limit):
        result = _blank_result("OMDb", str(show.get("id", "")), show.get("title", ""))
        result.update(
            {
                "description": show.get("overview"),
                "first_air_date": show.get("first_air_date") or None,
                "episode_runtime_minutes": show.get("episode_runtime_minutes"),
                "creators": show.get("creators") or [],
                "studios": show.get("studios") or [],
                "countries": show.get("countries") or [],
                "languages": show.get("languages") or [],
                "genres": show.get("genres") or [],
                "poster_url": show.get("poster_url"),
                "tmdb_score": show.get("vote_average"),
                "seasons": [],
                "url": show.get("url"),
            }
        )
        found.append(result)
    return found


def _run_tvmaze(query: str, limit: int, _ctx: ProviderContext) -> list[dict[str, Any]]:
    client = TVMazeClient()
    found: list[dict[str, Any]] = []
    for show in client.search(query, limit=limit):
        result = _blank_result("TVmaze", str(show.get("id", "")), show.get("title", ""))
        result.update(
            {
                "description": show.get("overview"),
                "first_air_date": show.get("first_air_date"),
                "episode_runtime_minutes": show.get("episode_runtime_minutes"),
                "studios": show.get("studios") or [],
                "countries": show.get("countries") or [],
                "genres": show.get("genres") or [],
                "poster_url": show.get("poster_url"),
                "tmdb_score": show.get("score"),
                "url": show.get("url"),
            }
        )
        found.append(result)
    return found


PROVIDERS: dict[str, ProviderSpec] = {
    "TMDB": ProviderSpec("TMDB", "primary", lambda ctx: bool(ctx.tmdb_api_key), _run_tmdb),
    "OMDb": ProviderSpec("OMDb", "primary", lambda ctx: bool(ctx.omdb_api_key), _run_omdb),
    # Keyless — always available, so TV search still returns real results
    # even before TMDB/OMDb are configured.
    "TVmaze": ProviderSpec("TVmaze", "primary", lambda ctx: True, _run_tvmaze),
}

DEFAULT_PROVIDER_ORDER = ["TMDB", "OMDb", "TVmaze"]


def search_tv_metadata(
    query: str,
    limit: int = 8,
    tmdb_api_key: str | None = None,
    omdb_api_key: str | None = None,
) -> dict[str, Any]:
    """Search TMDB and OMDb concurrently for TV shows and return
    normalized, creation-form-ready results, mirroring
    `search_movie_metadata`'s orchestration exactly (per-provider error
    isolation, title-match merging). TMDB results additionally carry a
    `seasons` list pulled straight from its `/tv/{id}` response, so a new
    show can bulk-create its seasons instead of the user typing them in."""
    ctx = ProviderContext(tmdb_api_key=tmdb_api_key, omdb_api_key=omdb_api_key)
    specs = [PROVIDERS[name] for name in DEFAULT_PROVIDER_ORDER if PROVIDERS[name].available(ctx)]

    results: list[dict[str, Any]] = []
    provider_errors: list[str] = []
    providers_used: list[str] = []

    def _call(spec: ProviderSpec) -> tuple[ProviderSpec, list[dict[str, Any]] | None, str | None]:
        try:
            return spec, spec.run(query, limit, ctx), None
        except Exception as exc:  # noqa: BLE001 — one provider's failure shouldn't sink the search
            return spec, None, str(exc)

    if specs:
        with ThreadPoolExecutor(max_workers=len(specs)) as executor:
            for spec, outcome, error in executor.map(_call, specs):
                if error is not None:
                    provider_errors.append(_friendly_provider_error(spec.name, error))
                    continue
                if outcome:
                    for candidate in outcome:
                        _merge_or_append(results, candidate)
                providers_used.append(spec.name)

    return {
        "query": query,
        "providers": providers_used,
        "provider_errors": provider_errors,
        "results": results,
    }
