"""Library ranks cover the whole library, not just the page or search shown."""

from decimal import Decimal

from src.database.models.movies import Movie
from src.database.session import SessionLocal
from tests.test_game_files_flow import game_flow  # noqa: F401  (registers the "flow" fixture)


async def _add(user_id, title: str, rating: str | None) -> str:
    async with SessionLocal() as db:
        movie = Movie(
            user_id=user_id,
            title=title,
            sort_title=title.lower(),
            rating_overall=Decimal(rating) if rating is not None else None,
        )
        db.add(movie)
        await db.commit()
        return str(movie.id)


async def test_ranks_span_the_library_even_when_searching_or_paging(flow) -> None:
    ten_a = await _add(flow.user_id, "Alpha", "10")
    ten_b = await _add(flow.user_id, "Bravo", "10")
    nine = await _add(flow.user_id, "Charlie", "9")
    unrated = await _add(flow.user_id, "Delta", None)

    everything = (await flow.client.get("/api/movie/list")).json()
    ranks = everything["score_ranks"]
    assert ranks == {ten_a: 1, ten_b: 2, nine: 3}
    assert unrated not in ranks

    # searching for one title still reports its place in the whole library
    searched = (await flow.client.get("/api/movie/list", params={"search": "Charlie"})).json()
    assert [m["title"] for m in searched["items"]] == ["Charlie"]
    assert searched["score_ranks"][nine] == 3

    # and a later page carries the same ranking
    paged = (await flow.client.get("/api/movie/list", params={"skip": 3, "limit": 1})).json()
    assert paged["score_ranks"] == ranks
