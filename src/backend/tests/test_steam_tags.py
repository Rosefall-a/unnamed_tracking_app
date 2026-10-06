"""Genre tags from the tags Steam players vote on."""

import json

import pytest

from src.features.metadata.games import steam_tags

# Elden Ring's tags as Steam lists them, most voted first
ELDEN_RING = [
    ("Souls-like", 7634),
    ("Open World", 5586),
    ("Dark Fantasy", 5321),
    ("RPG", 5086),
    ("Difficult", 4990),
    ("Action RPG", 3873),
    ("Multiplayer", 3699),
    ("Third Person", 3607),
    ("Fantasy", 3459),
    ("Singleplayer", 3357),
    ("Online Co-Op", 3226),
    ("Action", 3035),
    ("Co-op", 2604),
    ("Atmospheric", 2566),
    ("Great Soundtrack", 2500),
    ("PvP", 2461),
    ("Violent", 2418),
    ("3D", 2178),
    ("Character Customization", 1605),
    ("Family Friendly", 1450),
]


def _page(tags: list[tuple[str, int]]) -> str:
    payload = [{"tagid": i, "name": name, "count": votes, "browseable": True} for i, (name, votes) in enumerate(tags)]
    return f"<html><script>InitAppTagModal( 1245620, {json.dumps(payload)}, [], 'x' );</script></html>"


def test_tags_are_read_from_the_store_page_most_voted_first() -> None:
    shuffled = list(reversed(ELDEN_RING))
    assert steam_tags.parse_tags(_page(shuffled)) == ELDEN_RING


@pytest.mark.parametrize("html", ["", "<html>no tags here</html>", "InitAppTagModal( 1, [not json], [" + "]"])
def test_a_page_without_readable_tags_gives_none(html: str) -> None:
    assert steam_tags.parse_tags(html) == []


@pytest.mark.parametrize(
    "tag",
    ["Singleplayer", "Multiplayer", "Co-op", "Online Co-Op", "Local Co-Op", "PvP", "Controller",
     "Full controller support", "Steam Achievements", "Great Soundtrack", "Violent", "Family Friendly",
     "Early Access", "Free to Play", "VR", "3D", "Local Multiplayer"],
)
def test_tags_that_are_not_genres_are_dropped(tag: str) -> None:
    assert steam_tags.is_genre_tag(tag) is False


@pytest.mark.parametrize(
    "tag",
    ["Souls-like", "Open World", "Dark Fantasy", "RPG", "Difficult", "Action", "Metroidvania", "MMORPG", "Roguelike Deckbuilder"],
)
def test_genre_tags_are_kept(tag: str) -> None:
    assert steam_tags.is_genre_tag(tag) is True


def test_elden_ring_gets_its_real_genres_instead_of_just_action_rpg() -> None:
    picked = steam_tags.pick_genre_tags(ELDEN_RING, ["Action", "RPG"])
    assert picked[:6] == ["Souls-like", "Open World", "Dark Fantasy", "RPG", "Difficult", "Action RPG"]
    for noise in ("Multiplayer", "Singleplayer", "Online Co-Op", "Co-op", "PvP", "Great Soundtrack", "Violent"):
        assert noise not in picked
    # Action and RPG are there once each, not repeated from the official genres
    assert picked.count("RPG") == 1 and picked.count("Action") == 1


def test_official_genres_not_among_the_player_tags_are_added() -> None:
    picked = steam_tags.pick_genre_tags([("Souls-like", 900), ("RPG", 500)], ["Action", "RPG", "Adventure"])
    assert picked == ["Souls-like", "RPG", "Action", "Adventure"]


def test_a_barely_tagged_game_keeps_only_its_official_genres() -> None:
    assert steam_tags.pick_genre_tags([("Quirky", 3)], ["Indie", "Casual"]) == ["Indie", "Casual"]
    assert steam_tags.pick_genre_tags([], ["Indie"]) == ["Indie"]


def test_no_more_than_twelve_player_tags_are_kept() -> None:
    many = [(f"Genre {i}", 1000 - i) for i in range(30)]
    assert len(steam_tags.pick_genre_tags(many, [])) == steam_tags.MAX_TAGS


def test_an_unreachable_store_page_is_not_an_error(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise steam_tags.requests.ConnectionError("down")

    monkeypatch.setattr(steam_tags._store_session, "get", boom)
    monkeypatch.setattr(steam_tags, "_STORE_MIN_GAP", 0)
    assert steam_tags.fetch_player_tags(1) == []
    assert steam_tags.tags_with_player_votes(1, ["Action"]) == ["Action"]


# ---- the search result step

from src.features.metadata.games import search  # noqa: E402


def _result(app_id, title: str, tags: list[str]) -> dict:
    return {"title": title, "tags": tags, "steam_app_id": app_id, "steam_genres": ["Action", "RPG"]}


def test_a_steam_match_gets_the_player_tags_in_place_of_other_providers_genres(monkeypatch) -> None:
    monkeypatch.setattr(steam_tags, "fetch_player_tags", lambda app_id: ELDEN_RING)
    results = [_result(1245620, "Elden Ring", ["Role-playing (RPG)", "Adventure"])]
    search._apply_steam_user_tags(results, enabled=True)
    assert results[0]["tags"][:3] == ["Souls-like", "Open World", "Dark Fantasy"]
    assert "steam_genres" not in results[0]


def test_with_the_setting_off_the_tags_are_left_alone(monkeypatch) -> None:
    def forbidden(_app_id):
        raise AssertionError("must not fetch")

    monkeypatch.setattr(steam_tags, "fetch_player_tags", forbidden)
    results = [_result(1, "Elden Ring", ["Role-playing (RPG)"])]
    search._apply_steam_user_tags(results, enabled=False)
    assert results[0]["tags"] == ["Role-playing (RPG)"]
    assert "steam_genres" not in results[0]


def test_an_unreadable_store_page_keeps_the_existing_tags(monkeypatch) -> None:
    monkeypatch.setattr(steam_tags, "fetch_player_tags", lambda app_id: [])
    results = [_result(1, "Elden Ring", ["Adventure"])]
    search._apply_steam_user_tags(results, enabled=True)
    assert results[0]["tags"] == ["Adventure"]


def test_only_the_first_few_results_cost_a_store_request(monkeypatch) -> None:
    asked: list[int] = []
    monkeypatch.setattr(steam_tags, "fetch_player_tags", lambda app_id: asked.append(app_id) or ELDEN_RING)
    results = [_result(i, f"Game {i}", []) for i in range(1, 8)] + [{"title": "No Steam", "tags": ["X"]}]
    search._apply_steam_user_tags(results, enabled=True)
    assert asked == [1, 2, 3]


def test_the_preference_is_on_by_default_and_can_be_turned_off() -> None:
    from src.core.preferences import DEFAULTS, validate_preference

    assert DEFAULTS["steam_user_tags"] is True
    assert validate_preference("steam_user_tags", False) is False
    with pytest.raises(ValueError):
        validate_preference("steam_user_tags", "no")
