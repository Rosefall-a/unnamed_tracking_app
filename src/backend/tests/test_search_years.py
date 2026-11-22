"""Searching with a year ("Extinction 2015") finds that year's film, and two
titles with the same name from different years stay two results."""

import pytest

from src.features.metadata.movies import omdb as omdb_module
from src.features.metadata.movies import search as movie_search
from src.features.metadata.search_utils import merge_search_result, split_year, year_first


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Extinction 2015", ("Extinction", 2015)),
        ("Extinction (2015)", ("Extinction", 2015)),
        ("  Extinction, 2015 ", ("Extinction", 2015)),
        # a title that ends in a number keeps it
        ("Blade Runner 2049", ("Blade Runner 2049", None)),
        ("1917", ("1917", None)),
        ("2001: A Space Odyssey", ("2001: A Space Odyssey", None)),
        ("Up", ("Up", None)),
    ],
)
def test_a_year_typed_after_the_title_is_split_off(query, expected) -> None:
    assert split_year(query) == expected


def test_the_same_title_from_different_years_stays_two_results() -> None:
    results: list[dict] = []
    for year in ("2018", "2015"):
        merge_search_result(
            results, {"title": "Extinction", "year": year, "provider": "OMDb", "provider_id": year}
        )
    # a second provider's copy of the 2015 film fills in the existing one
    merge_search_result(
        results,
        {"title": "Extinction", "release_date": "2015-07-28", "description": "Ice age."},
    )
    assert [(r["year"], r.get("description")) for r in results] == [
        ("2018", None),
        ("2015", "Ice age."),
    ]
    assert [r["year"] for r in year_first(results, 2015)] == ["2015", "2018"]


class _FakeOMDb:
    """The OMDb answers for a search: by year when one is given."""

    asked: list[dict] = []

    def __init__(self, api_key=None, **_kwargs) -> None:
        self.api_key = api_key

    def _get(self, params):
        _FakeOMDb.asked.append(dict(params))
        if params.get("y") == "2015":
            return {"Search": [{"Title": "Extinction", "Year": "2015", "imdbID": "tt3467412"}]}
        if params["s"] == "Extinction":
            return {
                "Search": [
                    {"Title": "Extinction", "Year": "2018", "imdbID": "tt3201640"},
                    {"Title": "Extinction", "Year": "2015", "imdbID": "tt3467412"},
                ]
            }
        raise omdb_module.OMDBError("Movie not found!")

    search = omdb_module.OMDBClient.search


def test_omdb_is_asked_for_that_year_and_every_film_keeps_its_year(monkeypatch) -> None:
    monkeypatch.setattr(movie_search, "OMDBClient", _FakeOMDb)
    _FakeOMDb.asked = []
    found = movie_search.search_movie_metadata("Extinction 2015", 8, None, "key", light=True)
    assert _FakeOMDb.asked[0] == {"s": "Extinction", "type": "movie", "y": "2015"}
    assert [(r["title"], r["year"], r["provider_id"]) for r in found["results"]] == [
        ("Extinction", "2015", "tt3467412")
    ]
    found = movie_search.search_movie_metadata("Extinction", 8, None, "key", light=True)
    assert [(r["year"], r["provider_id"]) for r in found["results"]] == [
        ("2018", "tt3201640"),
        ("2015", "tt3467412"),
    ]


def test_a_number_that_was_part_of_the_name_is_searched_again_whole(monkeypatch) -> None:
    monkeypatch.setattr(movie_search, "OMDBClient", _FakeOMDb)
    _FakeOMDb.asked = []
    found = movie_search.search_movie_metadata("Zone 1999", 8, None, "key", light=True)
    assert found["results"] == []
    assert [a["s"] for a in _FakeOMDb.asked] == ["Zone", "Zone 1999"]
    assert "y" not in _FakeOMDb.asked[1]


def test_games_years_far_apart_are_two_games_but_one_year_is_the_same_game() -> None:
    from src.features.metadata.games.search import _merge_or_append

    results: list[dict] = []
    for year, provider in (("1993", "IGDB"), ("2016", "IGDB"), ("2017", "Steam")):
        _merge_or_append(
            results,
            {
                "title": "Doom",
                "release_date": f"{year}-05-13",
                "provider": provider,
                "provider_id": year,
                "links": [],
            },
        )
    # 1993 and 2016 stay apart; Steam's 2017 date is the 2016 game's store release
    assert [r["release_date"][:4] for r in results] == ["1993", "2016"]
