"""The library is read in the order it is shown, so the first page already holds the
best of the whole library, and ranks are only worked out for the first page."""

from src.database.models.movies import Movie
from src.database.session import SessionLocal
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def _add(user_id, title: str, rating) -> None:
    async with SessionLocal() as db:
        db.add(Movie(user_id=user_id, title=title, sort_title=title.lower(), rating_overall=rating))
        await db.commit()


async def _titles(flow, **params) -> list[str]:
    response = await flow.client.get("/api/movie/list", params=params)
    assert response.status_code == 200, response.text
    return [m["title"] for m in response.json()["items"]]


async def test_the_first_page_holds_the_best_titles_of_the_whole_library(flow) -> None:
    # six movies, rated 10 four times: a two-per-page sort of only the first page of
    # an A to Z list would show two of them
    for letter, rating in zip("ABCDEF", (5, 10, 3, 10, 10, 10), strict=True):
        await _add(flow.user_id, f"Movie {letter}", rating)
    first = await _titles(flow, sort="score", limit=4)
    assert set(first) == {"Movie B", "Movie D", "Movie E", "Movie F"}


async def test_unrated_titles_always_come_last(flow) -> None:
    await _add(flow.user_id, "Aaa unrated", None)
    await _add(flow.user_id, "Zzz rated", 1)
    assert await _titles(flow, sort="rank") == ["Zzz rated", "Aaa unrated"]


async def test_other_orders(flow) -> None:
    for name in ("Bravo", "Alpha", "Charlie"):
        await _add(flow.user_id, name, None)
    assert await _titles(flow, sort="title") == ["Alpha", "Bravo", "Charlie"]
    assert await _titles(flow, sort="title_desc") == ["Charlie", "Bravo", "Alpha"]


async def test_titles_with_the_same_name_do_not_repeat_or_vanish_between_pages(flow) -> None:
    for _ in range(5):
        await _add(flow.user_id, "Same Name", 7)
    seen: list[str] = []
    for skip in range(0, 5, 2):
        response = await flow.client.get("/api/movie/list", params={"sort": "score", "limit": 2, "skip": skip})
        seen += [m["id"] for m in response.json()["items"]]
    assert len(seen) == 5 and len(set(seen)) == 5


async def test_ranks_come_with_the_first_page_only(flow) -> None:
    await _add(flow.user_id, "Ranked", 9)
    first = (await flow.client.get("/api/movie/list", params={"limit": 1})).json()
    later = (await flow.client.get("/api/movie/list", params={"limit": 1, "skip": 1})).json()
    assert first["score_ranks"] and not later["score_ranks"]


async def test_an_unknown_sort_is_refused(flow) -> None:
    response = await flow.client.get("/api/movie/list", params={"sort": "nonsense"})
    assert response.status_code == 400
