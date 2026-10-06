"""Public search and retry behavior with offline provider responses."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.features.metadata import rate_limit
from src.features.metadata.anime import anilist, jikan, kitsu
from src.features.metadata.anime import search as anime_search
from src.features.metadata.movies import search as movie_search
from src.features.metadata.tv import search as tv_search


@pytest.mark.parametrize("module", [movie_search, tv_search])
def test_media_search_preserves_first_provider_and_fills_missing_fields(monkeypatch, module):
    primary = [{"id": 1, "title": "Example", "overview": "First description", "genres": []}]
    fallback = [
        {
            "id": "other-id",
            "title": "example™",
            "overview": "Fallback description",
            "genres": ["Drama"],
        }
    ]
    monkeypatch.setattr(
        module,
        "TMDBClient",
        lambda **_kwargs: SimpleNamespace(
            search=lambda *_a, **_k: primary, search_tv=lambda *_a, **_k: primary
        ),
    )
    monkeypatch.setattr(
        module,
        "OMDBClient",
        lambda **_kwargs: SimpleNamespace(
            search=lambda *_a, **_k: fallback, search_tv=lambda *_a, **_k: fallback
        ),
    )
    if module is tv_search:
        monkeypatch.setattr(
            module, "TVMazeClient", lambda: SimpleNamespace(search=lambda *_a, **_k: [])
        )
    operation = (
        module.search_movie_metadata if module is movie_search else module.search_tv_metadata
    )
    result = operation("Example", tmdb_api_key="test-tmdb", omdb_api_key="test-omdb")
    assert result["provider_errors"] == []
    assert len(result["results"]) == 1
    assert result["results"][0]["provider"] == "TMDB"
    assert result["results"][0]["provider_id"] == "1"
    assert result["results"][0]["description"] == "First description"
    assert result["results"][0]["genres"] == ["Drama"]


def test_anime_search_retains_successful_results_when_the_other_provider_fails(monkeypatch):
    monkeypatch.setattr(
        anime_search,
        "AniListClient",
        lambda: SimpleNamespace(search=lambda *_a, **_k: [{"id": 1, "title": "Example"}]),
    )
    unavailable = Mock()
    unavailable.search.side_effect = jikan.JikanError("429")
    monkeypatch.setattr(anime_search, "JikanClient", lambda: unavailable)
    result = anime_search.search_anime_metadata("Example")
    assert result["providers"] == ["AniList"]
    assert [entry["title"] for entry in result["results"]] == ["Example"]
    assert result["provider_errors"] == [
        "MyAnimeList: rate limited by the provider, try again in a few minutes."
    ]


@pytest.mark.parametrize(
    "module,client_type,error_type,operation",
    [
        (anilist, anilist.AniListClient, anilist.AniListError, "search"),
        (jikan, jikan.JikanClient, jikan.JikanError, "search"),
        (kitsu, kitsu.KitsuClient, kitsu.KitsuError, "find_exact"),
    ],
)
def test_rate_limits_keep_the_provider_error_type_and_bound_retries(
    monkeypatch, module, client_type, error_type, operation
):
    sleeps = []
    monkeypatch.setattr(rate_limit, "throttle", lambda *_a, **_k: None)
    monkeypatch.setattr(rate_limit.time, "sleep", sleeps.append)
    session = Mock()
    response = SimpleNamespace(status_code=429, headers={"Retry-After": "99"})
    session.get.return_value = session.post.return_value = response
    with pytest.raises(error_type, match="rate-limiting requests"):
        getattr(client_type(session=session), operation)("Example")
    requests_made = session.post.call_count if module is anilist else session.get.call_count
    assert requests_made == 4
    assert sleeps == [10, 10, 10]


def test_retry_header_and_exponential_fallback_preserve_delay(monkeypatch):
    sleeps = []
    monkeypatch.setattr(rate_limit, "throttle", lambda *_a, **_k: None)
    monkeypatch.setattr(rate_limit.time, "sleep", sleeps.append)
    session = Mock()
    session.post.side_effect = [
        SimpleNamespace(status_code=429, headers={"Retry-After": "0.5"}),
        SimpleNamespace(status_code=429, headers={"Retry-After": "invalid"}),
        SimpleNamespace(status_code=200, json=lambda: {"data": {"Page": {"media": []}}}),
    ]
    assert anilist.AniListClient(session=session).search("Example") == []
    assert sleeps == [0.5, 4]
