from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Literal

from src.features.metadata.anime.anilist import AniListClient
from src.features.metadata.anime.jikan import JikanClient

# Unlike Movies/TV (TMDB+OMDb, both need an app-wide API key), both
# AniList and Jikan are public/keyless for read-only search — so there's
# no ProviderContext of credentials to gate on here, both providers
# always run. Redundancy is still the point: AniList is the primary,
# anime-specific source; Jikan (MyAnimeList) is the fallback, so a rate
# limit or an AniList outage doesn't leave the search empty.


def _blank_result(provider: str, provider_id: str, title: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "provider_id": provider_id,
        "title": title,
        "description": None,
        "first_air_date": None,
        "episode_runtime_minutes": None,
        "episode_count": None,
        "studios": [],
        "countries": [],
        "genres": [],
        "poster_url": None,
        "backdrop_url": None,
        "format": None,
        "anilist_score": None,
        "mal_score": None,
        # Jikan's own id for this entry — kept separate from `provider_id`
        # (which is whichever provider matched first, usually AniList)
        # since episode sync specifically needs Jikan's id to call back in.
        "mal_id": None,
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
    a visually duplicate second result."""
    for existing in results:
        if _titles_match(existing["title"], candidate["title"]):
            for key, value in candidate.items():
                if key in ("provider", "provider_id", "title"):
                    continue
                if not existing.get(key) and value:
                    existing[key] = value
            return
    results.append(candidate)


ProviderRun = Callable[[str, int], list[dict[str, Any]]]


@dataclass
class ProviderSpec:
    name: str
    kind: Literal["primary"]
    run: ProviderRun


def _run_anilist(query: str, limit: int) -> list[dict[str, Any]]:
    client = AniListClient()
    found: list[dict[str, Any]] = []
    for entry in client.search(query, limit=limit):
        result = _blank_result("AniList", str(entry.get("id", "")), entry.get("title") or "")
        result.update(
            {
                "description": entry.get("overview"),
                "first_air_date": entry.get("release_date"),
                "episode_runtime_minutes": entry.get("episode_runtime_minutes"),
                "episode_count": entry.get("episode_count"),
                "studios": entry.get("studios") or [],
                "countries": entry.get("countries") or [],
                "genres": entry.get("genres") or [],
                "poster_url": entry.get("poster_url"),
                "backdrop_url": entry.get("backdrop_url"),
                "format": entry.get("format"),
                "anilist_score": entry.get("score"),
                "url": entry.get("url"),
                # AniList exposes each entry's own MyAnimeList id directly,
                # so a show found via AniList alone can still get a real
                # Jikan fallback later (once Jikan is reachable) instead of
                # needing MAL's own search to separately find and match it.
                "mal_id": str(entry["id_mal"]) if entry.get("id_mal") else None,
            }
        )
        found.append(result)
    return found


def _run_jikan(query: str, limit: int) -> list[dict[str, Any]]:
    client = JikanClient()
    found: list[dict[str, Any]] = []
    for entry in client.search(query, limit=limit):
        result = _blank_result("MyAnimeList", str(entry.get("id", "")), entry.get("title") or "")
        result.update(
            {
                "description": entry.get("overview"),
                "first_air_date": entry.get("release_date"),
                "episode_runtime_minutes": entry.get("episode_runtime_minutes"),
                "episode_count": entry.get("episode_count"),
                "studios": entry.get("studios") or [],
                "countries": entry.get("countries") or [],
                "genres": entry.get("genres") or [],
                "mal_id": str(entry.get("id", "")) or None,
                "poster_url": entry.get("poster_url"),
                "format": entry.get("format"),
                "mal_score": entry.get("score"),
                "url": entry.get("url"),
            }
        )
        found.append(result)
    return found


PROVIDERS: list[ProviderSpec] = [
    ProviderSpec("AniList", "primary", _run_anilist),
    ProviderSpec("MyAnimeList", "primary", _run_jikan),
]


def search_anime_metadata(query: str, limit: int = 8) -> dict[str, Any]:
    """Search AniList and Jikan concurrently and return normalized,
    creation-form-ready results. Both providers are keyless, so unlike
    Movies/TV's search there's nothing to gate on — both always run.
    A provider that fails at request time contributes a message to
    `provider_errors` without failing the other provider."""
    results: list[dict[str, Any]] = []
    provider_errors: list[str] = []
    providers_used: list[str] = []

    def _call(spec: ProviderSpec) -> tuple[ProviderSpec, list[dict[str, Any]] | None, str | None]:
        try:
            return spec, spec.run(query, limit), None
        except Exception as exc:  # noqa: BLE001 — one provider's failure shouldn't sink the search
            return spec, None, str(exc)

    with ThreadPoolExecutor(max_workers=len(PROVIDERS)) as executor:
        for spec, outcome, error in executor.map(_call, PROVIDERS):
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
