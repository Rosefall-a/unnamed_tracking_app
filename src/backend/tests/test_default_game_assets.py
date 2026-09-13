from uuid import UUID

from src.api.routes.default_game_assets import _default_cover_svg


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
