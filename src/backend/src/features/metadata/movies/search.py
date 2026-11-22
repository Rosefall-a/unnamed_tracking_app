# pylint: disable=duplicate-code
# These modules intentionally keep domain/provider-specific logic separate; similar
# structures here represent parallel APIs rather than accidental copy/paste.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from src.features.metadata.movies.omdb import OMDBClient
from src.features.metadata.movies.tmdb import TMDBClient
from src.features.metadata.search_utils import (
    format_provider_error,
    merge_search_result,
    run_providers,
    split_year,
    visible_errors,
    year_first,
)


def _blank_result(provider: str, provider_id: str, title: str) -> dict[str, Any]:
    """A normalized result dict with every field present — providers fill
    in what they know and leave the rest at these defaults."""
    return {
        "provider": provider,
        "provider_id": provider_id,
        "title": title,
        "description": None,
        "release_date": None,
        "year": None,
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


@dataclass
class ProviderContext:
    tmdb_api_key: str | None
    omdb_api_key: str | None
    # a quick search for a results list: no detail page per result
    light: bool = False
    # a year typed after the title, which providers that can search by year use
    year: int | None = None


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
    for movie in client.search(query, limit=limit, year=ctx.year, light=ctx.light):
        result = _blank_result("TMDB", str(movie.get("id", "")), movie.get("title", ""))
        result.update(
            {
                "description": movie.get("overview"),
                "release_date": movie.get("release_date") or None,
                "year": (movie.get("release_date") or "")[:4] or None,
                "runtime_minutes": movie.get("runtime_minutes"),
                "director": movie.get("director"),
                "writer": movie.get("writer"),
                "studios": movie.get("studios") or [],
                "countries": movie.get("countries") or [],
                "languages": movie.get("languages") or [],
                "genres": movie.get("genres") or [],
                "poster_url": movie.get("poster_url"),
                "backdrop_url": movie.get("backdrop_url"),
                "tmdb_score": movie.get("vote_average"),
                "url": movie.get("url"),
            }
        )
        found.append(result)
    return found


def _run_omdb(query: str, limit: int, ctx: ProviderContext) -> list[dict[str, Any]]:
    assert ctx.omdb_api_key  # guarded by `available`
    client = OMDBClient(api_key=ctx.omdb_api_key)
    found: list[dict[str, Any]] = []
    for movie in client.search(query, limit=limit, light=ctx.light, year=ctx.year):
        result = _blank_result("OMDb", str(movie.get("id", "")), movie.get("title", ""))
        result.update(
            {
                "description": movie.get("overview"),
                "release_date": movie.get("release_date") or None,
                "year": movie.get("year"),
                "runtime_minutes": movie.get("runtime_minutes"),
                "director": movie.get("director"),
                "writer": movie.get("writer"),
                "studios": movie.get("studios") or [],
                "countries": movie.get("countries") or [],
                "languages": movie.get("languages") or [],
                "genres": movie.get("genres") or [],
                "poster_url": movie.get("poster_url"),
                "tmdb_score": movie.get("vote_average"),
                "url": movie.get("url"),
            }
        )
        found.append(result)
    return found


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
    light: bool = False,
) -> dict[str, Any]:
    """A year typed after the title ("Extinction 2015") is searched as the
    year it came out, not as part of the name, and that year's movies come
    first. When the title without it finds nothing, the whole text is
    searched again, so a name that ends in a number is never lost."""
    title, year = split_year(query)
    found = _search(title, limit, tmdb_api_key, omdb_api_key, light, year)
    if year is not None and not found["results"]:
        found = _search(query.strip(), limit, tmdb_api_key, omdb_api_key, light, None)
    found["query"] = query
    found["results"] = year_first(found["results"], year)
    return found


def _search(
    query: str,
    limit: int,
    tmdb_api_key: str | None,
    omdb_api_key: str | None,
    light: bool,
    year: int | None,
) -> dict[str, Any]:
    """Search TMDB and OMDb concurrently and return normalized,
    creation-form-ready results. Two sources on purpose — redundancy, so a
    missing/rate-limited/unconfigured source doesn't leave the search empty.
    A provider missing its API key is silently skipped, not an error;
    a provider that's configured but fails at request time contributes a
    message to `provider_errors` without failing the other provider."""
    ctx = ProviderContext(
        tmdb_api_key=tmdb_api_key, omdb_api_key=omdb_api_key, light=light, year=year
    )
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
        for spec, outcome, error in run_providers(specs, _call):
            if error is not None:
                provider_errors.append(format_provider_error(spec.name, error))
                continue
            if outcome:
                for candidate in outcome:
                    merge_search_result(results, candidate)
            providers_used.append(spec.name)

    return {
        "query": query,
        "providers": providers_used,
        "provider_errors": visible_errors(provider_errors, bool(results)),
        "results": results,
    }
