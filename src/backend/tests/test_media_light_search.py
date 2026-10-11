"""Movie and TV list searches skip the per-result detail page; the full search keeps it."""

import pytest

from src.features.metadata.movies.omdb import OMDBClient
from src.features.metadata.movies.tmdb import TMDBClient

_MOVIES = [
    {"id": 1, "title": "Inception", "overview": "Dreams.", "release_date": "2010-07-16", "poster_path": "/i.jpg"},
    {"id": 2, "title": "Interstellar", "overview": "Space.", "release_date": "2014-11-05", "poster_path": "/s.jpg"},
]
_SHOWS = [
    {"id": 10, "name": "Breaking Bad", "overview": "Chemistry.", "first_air_date": "2008-01-20", "poster_path": "/b.jpg"},
    {"id": 11, "name": "Better Call Saul", "overview": "Law.", "first_air_date": "2015-02-08", "poster_path": "/c.jpg"},
]


@pytest.fixture
def tmdb(monkeypatch):
    calls: list[str] = []

    def fake_get(_self, path, _params=None):
        calls.append(path)
        if path == "/search/movie":
            return {"results": _MOVIES}
        if path == "/search/tv":
            return {"results": _SHOWS}
        if path.startswith("/movie/"):
            return {"title": "Detail", "runtime": 148, "credits": {"crew": [{"job": "Director", "name": "N"}]}}
        return {"name": "Detail", "seasons": []}

    monkeypatch.setattr(TMDBClient, "_get", fake_get)
    return calls


def test_a_light_movie_search_reads_only_the_search_answer(tmdb) -> None:
    found = TMDBClient("key").search("inception", limit=8, light=True)
    assert tmdb == ["/search/movie"]
    assert [m["title"] for m in found] == ["Inception", "Interstellar"]
    assert found[0]["poster_url"] and found[0]["release_date"] == "2010-07-16"


def test_a_full_movie_search_reads_a_detail_page_per_result(tmdb) -> None:
    found = TMDBClient("key").search("inception", limit=8)
    assert tmdb == ["/search/movie", "/movie/1", "/movie/2"]
    assert found[0]["runtime_minutes"] == 148 and found[0]["director"] == "N"


def test_a_light_tv_search_reads_only_the_search_answer(tmdb) -> None:
    found = TMDBClient("key").search_tv("breaking", limit=8, light=True)
    assert tmdb == ["/search/tv"]
    assert len(found) == 2


def test_a_full_tv_search_reads_a_detail_page_per_result(tmdb) -> None:
    TMDBClient("key").search_tv("breaking", limit=8)
    assert tmdb == ["/search/tv", "/tv/10", "/tv/11"]


@pytest.fixture
def omdb(monkeypatch):
    calls: list[dict] = []

    def fake_get(_self, params):
        calls.append(dict(params))
        if "s" in params:
            return {"Search": [{"Title": "Inception", "imdbID": "tt1375666", "Poster": "N/A"}, {"Title": "Other", "imdbID": "tt0000002"}]}
        return {"Title": "Inception", "Plot": "Dreams.", "Runtime": "148 min", "imdbRating": "8.8"}

    monkeypatch.setattr(OMDBClient, "_get", fake_get)
    return calls


def test_a_light_omdb_search_reads_no_title_pages(omdb) -> None:
    found = OMDBClient("key").search("inception", limit=8, light=True)
    assert [list(c) for c in omdb] == [["s", "type"]]
    assert [m["title"] for m in found] == ["Inception", "Other"]


def test_a_full_omdb_search_reads_a_title_page_per_result(omdb) -> None:
    OMDBClient("key").search("inception", limit=8)
    assert [c.get("i") for c in omdb if "i" in c] == ["tt1375666", "tt0000002"]
