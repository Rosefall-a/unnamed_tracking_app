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


# ---- progress: worked out in the query, so the first page is the furthest along ----


async def _show(user_id, title: str, seasons: list[tuple[int | None, int]]) -> None:
    from src.database.models.tv_show import TVSeason, TVShow

    async with SessionLocal() as db:
        show = TVShow(user_id=user_id, title=title, sort_title=title.lower())
        db.add(show)
        await db.flush()
        for number, (count, watched) in enumerate(seasons, start=1):
            db.add(
                TVSeason(
                    show_id=show.id,
                    season_number=number,
                    episode_count=count,
                    episodes_watched=watched,
                )
            )
        await db.commit()


async def test_progress_sort_puts_finished_shows_first_across_the_whole_library(flow) -> None:
    # A to Z, the finished ones come last, so a first page sorted only in the
    # browser would hold none of them
    await _show(flow.user_id, "Aaa half", [(10, 5)])
    await _show(flow.user_id, "Bbb none", [(10, 0)])
    await _show(flow.user_id, "Ccc unknown length", [(10, 10), (None, 3)])
    await _show(flow.user_id, "Ddd no seasons", [])
    await _show(flow.user_id, "Yyy done", [(10, 10)])
    await _show(flow.user_id, "Zzz done", [(6, 6), (4, 4)])
    response = await flow.client.get("/api/tv/list", params={"sort": "progress", "limit": 3})
    assert response.status_code == 200, response.text
    assert [s["title"] for s in response.json()["items"]] == ["Yyy done", "Zzz done", "Aaa half"]
    response = await flow.client.get(
        "/api/tv/list", params={"sort": "progress", "limit": 3, "skip": 3}
    )
    # nothing to go on counts as 0, then A to Z, as the cards show it
    assert [s["title"] for s in response.json()["items"]] == [
        "Bbb none",
        "Ccc unknown length",
        "Ddd no seasons",
    ]


async def test_progress_sort_for_movies_counts_watched_as_finished(flow) -> None:
    from src.database.models.movies import MovieStatus

    async with SessionLocal() as db:
        db.add_all(
            [
                Movie(user_id=flow.user_id, title="Aaa plan", sort_title="aaa plan"),
                Movie(
                    user_id=flow.user_id,
                    title="Bbb part way",
                    sort_title="bbb part way",
                    progress_minutes=30,
                    runtime_minutes=120,
                ),
                Movie(
                    user_id=flow.user_id,
                    title="Zzz watched",
                    sort_title="zzz watched",
                    status=MovieStatus.WATCHED,
                ),
            ]
        )
        await db.commit()
    assert await _titles(flow, sort="progress") == ["Zzz watched", "Bbb part way", "Aaa plan"]
