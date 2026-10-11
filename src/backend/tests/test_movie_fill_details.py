"""Movies saved without a length get it (and other empty details) from a lookup."""

from datetime import date
from types import SimpleNamespace

from src.api.routes import movies as movie_routes
from src.database.models.movies import Movie
from src.database.session import SessionLocal
from src.features.metadata.movies.fill_details import fill_empty_fields, same_movie
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)

_FOUND = {
    "title": "Inception",
    "release_date": "2010-07-16",
    "runtime_minutes": 148,
    "description": "Dreams within dreams.",
    "director": "Christopher Nolan",
    "genres": ["Science Fiction"],
    "studios": [],
}


def test_the_same_title_and_year_is_the_same_movie() -> None:
    movie = Movie(title="Inception", release_date=date(2010, 7, 16))
    assert same_movie(movie, _FOUND)
    assert same_movie(Movie(title="inception!"), _FOUND)  # no year known: the title decides


def test_a_remake_with_the_same_name_is_not() -> None:
    assert not same_movie(Movie(title="Inception", release_date=date(1999, 1, 1)), _FOUND)
    assert not same_movie(Movie(title="Interstellar"), _FOUND)


def test_only_empty_unlocked_fields_are_filled() -> None:
    movie = Movie(title="Inception", description="my own words", locked_fields=["director"], genres=[])
    assert fill_empty_fields(movie, _FOUND)
    assert movie.runtime_minutes == 148
    assert movie.description == "my own words"  # something was already there
    assert movie.director is None  # the person locked it
    assert movie.genres == ["Science Fiction"]


def test_nothing_new_means_nothing_changed() -> None:
    movie = Movie(title="Inception", runtime_minutes=148, description="d", director="x", genres=["g"])
    assert not fill_empty_fields(movie, {**_FOUND, "genres": []})


def _with_a_key(monkeypatch) -> None:
    monkeypatch.setattr(
        movie_routes,
        "resolve_integrations",
        lambda _row: SimpleNamespace(tmdb_api_key="key", omdb_api_key=None),
    )


async def _add(user_id, title: str, **fields) -> str:
    async with SessionLocal() as db:
        movie = Movie(user_id=user_id, title=title, sort_title=title.lower(), **fields)
        db.add(movie)
        await db.commit()
        return str(movie.id)


async def test_without_a_tmdb_or_omdb_key_it_says_so(flow, monkeypatch) -> None:
    monkeypatch.setattr(
        movie_routes,
        "resolve_integrations",
        lambda _row: SimpleNamespace(tmdb_api_key=None, omdb_api_key=None),
    )
    response = await flow.client.post("/api/movie/fill-details")
    assert response.status_code == 400 and "API key" in response.json()["detail"]


async def test_the_route_fills_the_length_a_few_at_a_time(flow, monkeypatch) -> None:
    _with_a_key(monkeypatch)
    monkeypatch.setattr(
        movie_routes,
        "search_movie_metadata",
        lambda title, *_a: {"results": [_FOUND] if title == "Inception" else []},
    )
    first = await _add(flow.user_id, "Inception", release_date=date(2010, 7, 16))
    await _add(flow.user_id, "Unknown Film")
    await _add(flow.user_id, "Already Has One", runtime_minutes=90)

    done = (await flow.client.post("/api/movie/fill-details")).json()
    assert done == {"checked": 2, "filled": 1, "next": None}

    page = (await flow.client.get("/api/movie/list")).json()["items"]
    by_title = {m["title"]: m for m in page}
    assert by_title["Inception"]["runtime_minutes"] == 148
    assert by_title["Unknown Film"]["runtime_minutes"] is None
    assert by_title["Already Has One"]["runtime_minutes"] == 90
    assert first


async def test_the_route_pages_with_a_cursor(flow, monkeypatch) -> None:
    _with_a_key(monkeypatch)
    monkeypatch.setattr(movie_routes, "search_movie_metadata", lambda *_a: {"results": []})
    for n in range(3):
        await _add(flow.user_id, f"Film {n}")
    one = (await flow.client.post("/api/movie/fill-details", params={"limit": 2})).json()
    assert one["checked"] == 2 and one["next"]
    two = (await flow.client.post("/api/movie/fill-details", params={"limit": 2, "after": one["next"]})).json()
    assert two["checked"] == 1 and two["next"] is None
