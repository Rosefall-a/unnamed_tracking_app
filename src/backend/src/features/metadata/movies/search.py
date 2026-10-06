# These modules intentionally keep domain/provider-specific logic separate; similar
# structures here represent parallel APIs rather than accidental copy/paste.

from __future__ import annotations

from functools import partial
from typing import Any

from src.features.metadata.movies.omdb import OMDBClient
from src.features.metadata.movies.tmdb import TMDBClient
from src.features.metadata.search_utils import (
    MediaProviderContext as ProviderContext,
)
from src.features.metadata.search_utils import (
    MediaProviderSpec as ProviderSpec,
)
from src.features.metadata.search_utils import (
    search_providers,
)


# These distinct media DTOs share identity fields but preserve their own result schemas.
# pylint: disable=duplicate-code
def _blank_result(provider: str, provider_id: str, title: str) -> dict[str, Any]:
    """A normalized result dict with every field present — providers fill
    in what they know and leave the rest at these defaults."""
    return {
        "provider": provider,
        "provider_id": provider_id,
        "title": title,
        "description": None,
        "release_date": None,
        "runtime_minutes": None,
        "director": None,
        "writer": None,
        "studios": [],
        "countries": [],
        "languages": [],
        "genres": [],
        "poster_url": None,
        "backdrop_url": None,
        "tmdb_score": None,
        "url": None,
    }


# pylint: enable=duplicate-code


def _movie_result(provider: str, movie: dict[str, Any]) -> dict[str, Any]:
    result = _blank_result(provider, str(movie.get("id", "")), movie.get("title", ""))
    result.update(
        {
            "description": movie.get("overview"),
            "release_date": movie.get("release_date") or None,
            "runtime_minutes": movie.get("runtime_minutes"),
            "director": movie.get("director"),
            "writer": movie.get("writer"),
            "studios": movie.get("studios") or [],
            "countries": movie.get("countries") or [],
            "languages": movie.get("languages") or [],
            "genres": movie.get("genres") or [],
            "poster_url": movie.get("poster_url"),
            "backdrop_url": movie.get("backdrop_url") if provider == "TMDB" else None,
            "tmdb_score": movie.get("vote_average"),
            "url": movie.get("url"),
        }
    )
    return result


def _run_tmdb(query: str, limit: int, ctx: ProviderContext) -> list[dict[str, Any]]:
    assert ctx.tmdb_api_key  # guarded by `available`
    return [
        _movie_result("TMDB", item)
        for item in TMDBClient(api_key=ctx.tmdb_api_key).search(query, limit=limit)
    ]


def _run_omdb(query: str, limit: int, ctx: ProviderContext) -> list[dict[str, Any]]:
    assert ctx.omdb_api_key  # guarded by `available`
    return [
        _movie_result("OMDb", item)
        for item in OMDBClient(api_key=ctx.omdb_api_key).search(query, limit=limit)
    ]


PROVIDERS: dict[str, ProviderSpec] = {
    "TMDB": ProviderSpec("TMDB", "primary", lambda ctx: bool(ctx.tmdb_api_key), _run_tmdb),
    "OMDb": ProviderSpec("OMDb", "primary", lambda ctx: bool(ctx.omdb_api_key), _run_omdb),
}

DEFAULT_PROVIDER_ORDER = ["TMDB", "OMDb"]


def search_movie_metadata(
    query: str,
    limit: int = 8,
    tmdb_api_key: str | None = None,
    omdb_api_key: str | None = None,
) -> dict[str, Any]:
    """Search TMDB and OMDb concurrently and return normalized,
    creation-form-ready results. Two sources on purpose — redundancy, so a
    missing/rate-limited/unconfigured source doesn't leave the search empty.
    A provider missing its API key is silently skipped, not an error;
    a provider that's configured but fails at request time contributes a
    message to `provider_errors` without failing the other provider."""
    ctx = ProviderContext(tmdb_api_key=tmdb_api_key, omdb_api_key=omdb_api_key)
    specs = [PROVIDERS[name] for name in DEFAULT_PROVIDER_ORDER if PROVIDERS[name].available(ctx)]

    result = search_providers([(spec.name, partial(spec.run, query, limit, ctx)) for spec in specs])
    return {"query": query, **result}
