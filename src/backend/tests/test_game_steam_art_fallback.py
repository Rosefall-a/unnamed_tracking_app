"""A Steam game the image providers had no art for falls back to Steam's own."""

from types import SimpleNamespace

import requests

from src.features.metadata.games import search
from src.features.metadata.games.search import _add_steam_art_fallback, _steam_art_exists

APP = 1145360
COVER = f"https://cdn.akamai.steamstatic.com/steam/apps/{APP}/library_600x900.jpg"
HERO = f"https://cdn.akamai.steamstatic.com/steam/apps/{APP}/library_hero.jpg"


def _result(**fields) -> dict:
    return {
        "title": "Hades",
        "steam_app_id": APP,
        "key_art_url": None,
        "key_art_urls": [],
        "banner_url": None,
        "banner_urls": [],
        **fields,
    }


def test_a_game_with_no_art_gets_steams_cover_and_banner(monkeypatch) -> None:
    monkeypatch.setattr(search, "_steam_art_exists", lambda url: True)
    result = _result()
    _add_steam_art_fallback([result])
    assert result["key_art_url"] == COVER and result["key_art_urls"] == [COVER]
    assert result["banner_url"] == HERO and result["banner_urls"] == [HERO]


def test_only_what_steam_has_is_used(monkeypatch) -> None:
    monkeypatch.setattr(search, "_steam_art_exists", lambda url: url == HERO)
    result = _result()
    _add_steam_art_fallback([result])
    assert result["key_art_url"] is None  # no portrait cover: the wide header is never cropped in
    assert result["banner_url"] == HERO


def test_art_an_image_provider_found_is_never_replaced(monkeypatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(search, "_steam_art_exists", lambda url: asked.append(url) or True)
    result = _result(key_art_url="https://grids/mine.png", key_art_urls=["https://grids/mine.png"])
    _add_steam_art_fallback([result])
    assert result["key_art_url"] == "https://grids/mine.png"
    assert COVER not in asked  # not even looked up
    assert result["banner_url"] == HERO


def test_a_game_that_is_not_from_steam_is_left_alone(monkeypatch) -> None:
    monkeypatch.setattr(search, "_steam_art_exists", lambda url: True)
    result = _result(steam_app_id=None)
    _add_steam_art_fallback([result])
    assert result["key_art_url"] is None and result["banner_url"] is None


def test_asking_steam_whether_art_exists(monkeypatch) -> None:
    def head(status, kind="image/jpeg"):
        return lambda *_a, **_k: SimpleNamespace(status_code=status, headers={"content-type": kind})

    monkeypatch.setattr(search.steam.SESSION, "head", head(200))
    assert _steam_art_exists(COVER)
    monkeypatch.setattr(search.steam.SESSION, "head", head(404))
    assert not _steam_art_exists(COVER)
    monkeypatch.setattr(search.steam.SESSION, "head", head(200, "text/html"))
    assert not _steam_art_exists(COVER)

    def down(*_a, **_k):
        raise requests.ConnectionError("no route")

    monkeypatch.setattr(search.steam.SESSION, "head", down)
    assert not _steam_art_exists(COVER)  # no answer means no fallback, not an error
