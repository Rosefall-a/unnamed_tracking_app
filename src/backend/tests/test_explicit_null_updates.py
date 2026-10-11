"""A PATCH that sends null for a column that cannot be null leaves it alone
(instead of failing in the database), and still clears one that can be empty."""

from src.database.models.movies import Movie
from src.database.session import SessionLocal
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def _movie(user_id) -> str:
    async with SessionLocal() as db:
        movie = Movie(
            user_id=user_id, title="Keep Me", sort_title="keep me", favorite=True, description="a note"
        )
        db.add(movie)
        await db.commit()
        return str(movie.id)


async def test_null_for_a_required_field_means_no_change(flow) -> None:
    movie_id = await _movie(flow.user_id)
    response = await flow.client.patch(
        f"/api/movie/update/{movie_id}", json={"title": None, "favorite": None, "status": None}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Keep Me" and body["favorite"] is True


async def test_null_for_an_optional_field_still_clears_it(flow) -> None:
    movie_id = await _movie(flow.user_id)
    response = await flow.client.patch(f"/api/movie/update/{movie_id}", json={"description": None})
    assert response.status_code == 200, response.text
    assert response.json()["description"] is None
