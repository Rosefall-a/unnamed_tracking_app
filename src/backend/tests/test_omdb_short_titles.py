"""A short title such as "F1" matches so much that OMDb refuses the search; the
search then asks for that exact title, so it can still be found and added."""

from src.features.metadata.movies.omdb import OMDBClient


class _Reply:
    status_code = 200

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.text = ""

    def json(self) -> dict:
        return self._payload


class _Session:
    """Answers like OMDb: a search for "F1" is too broad, the exact title is not."""

    def __init__(self) -> None:
        self.asked: list[dict] = []

    def get(self, _url: str, params: dict, timeout: int) -> _Reply:
        del timeout
        self.asked.append({k: v for k, v in params.items() if k != "apikey"})
        if "s" in params:
            return _Reply({"Response": "False", "Error": "Too many results."})
        if params.get("t") == "F1":
            return _Reply(
                {
                    "Response": "True",
                    "Title": "F1: The Movie",
                    "Year": "2025",
                    "Released": "27 Jun 2025",
                    "Plot": "A racing driver returns.",
                    "Runtime": "156 min",
                    "imdbID": "tt16311594",
                    "imdbRating": "7.7",
                }
            )
        return _Reply({"Response": "False", "Error": "Movie not found!"})


def test_a_too_broad_short_title_is_found_by_its_exact_name() -> None:
    session = _Session()
    found = OMDBClient("key", session=session).search("F1")
    assert [(r["title"], r["year"], r["runtime_minutes"]) for r in found] == [
        ("F1: The Movie", "2025", 156)
    ]
    # the search, then the exact title; the exact answer is already the full
    # record, so there is no third request for its details
    assert session.asked == [{"s": "F1", "type": "movie"}, {"t": "F1", "type": "movie"}]


def test_the_exact_name_keeps_the_kind_and_year() -> None:
    session = _Session()
    assert OMDBClient("key", session=session).search_tv("Zz", year=2020) == []
    assert session.asked[-1] == {"t": "Zz", "type": "series", "y": "2020"}


class _OldFirstSession:
    """OMDb lists the old films of a name first; the new one is only found by
    asking for that exact name in its year."""

    def __init__(self, year: int) -> None:
        self.year = str(year)
        self.asked: list[dict] = []

    def get(self, _url: str, params: dict, timeout: int) -> _Reply:
        del timeout
        self.asked.append({k: v for k, v in params.items() if k != "apikey"})
        if "s" in params:
            return _Reply(
                {
                    "Response": "True",
                    "Search": [
                        {"Title": "Resident Evil: Apocalypse", "Year": "2004", "imdbID": "tt2"},
                        {"Title": "Resident Evil", "Year": "2002", "imdbID": "tt1"},
                    ],
                }
            )
        if params.get("t") == "Resident Evil" and params.get("y") == self.year:
            return _Reply(
                {
                    "Response": "True",
                    "Title": "Resident Evil",
                    "Year": self.year,
                    "Plot": "A new one.",
                    "imdbID": "tt3",
                }
            )
        return _Reply({"Response": "False", "Error": "Movie not found!"})


def test_a_new_film_with_an_old_name_is_found_and_exact_names_come_first() -> None:
    from datetime import date

    session = _OldFirstSession(date.today().year)
    found = OMDBClient("key", session=session).search("Resident Evil", light=True)
    # the films called exactly that first (OMDb's order), then longer names
    assert [(r["title"], r["year"]) for r in found] == [
        ("Resident Evil", "2002"),
        ("Resident Evil", str(date.today().year)),
        ("Resident Evil: Apocalypse", "2004"),
    ]
    # one search plus the exact name for next year and this year, nothing more
    assert len(session.asked) == 3


def test_a_year_typed_in_puts_the_exact_name_from_that_year_first() -> None:
    from src.features.metadata.search_utils import year_first

    results = [
        {"title": "Resident Evil Requiem - Evil Has Always Had A Name", "year": "2026"},
        {"title": "Resident Evil", "year": "2002"},
        {"title": "Resident Evil", "year": "2026"},
    ]
    assert [(r["title"], r["year"]) for r in year_first(results, 2026, "Resident Evil")] == [
        ("Resident Evil", "2026"),
        ("Resident Evil Requiem - Evil Has Always Had A Name", "2026"),
        ("Resident Evil", "2002"),
    ]
