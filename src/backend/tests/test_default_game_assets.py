from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.default_game_assets import _default_cover_svg, router
from src.core.auth import get_current_user


def test_default_cover_svg_is_deterministic_and_title_aware() -> None:
    game_id = UUID("00000000-0000-0000-0000-000000000001")

    first = _default_cover_svg(game_id, "My Game")
    second = _default_cover_svg(game_id, "My Game")

    assert first == second
    assert 'aria-label="My Game default cover"' in first
    assert "NO COVER ART" in first


def test_default_cover_svg_escapes_title() -> None:
    game_id = UUID("00000000-0000-0000-0000-000000000002")

    svg = _default_cover_svg(game_id, "Tom & <Jerry>")

    assert "Tom &amp; &lt;Jerry&gt;" in svg
    assert "Tom & <Jerry>" not in svg


def test_preview_reuses_fallback_art_without_creating_a_game() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    with TestClient(app) as client:
        response = client.get("/api/game/preview-cover", params={"title": "Tom & <Jerry>"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        assert response.text == _default_cover_svg(
            UUID("00000000-0000-0000-0000-000000000001"), "Tom & <Jerry>"
        )
        assert client.get("/api/game/preview-cover", params={"title": "x" * 81}).status_code == 422
