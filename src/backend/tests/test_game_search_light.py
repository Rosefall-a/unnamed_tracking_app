"""The Add Game list is a quick search; details are read for the game that is picked."""

import pytest

from src.features.metadata.games import search


def _boom(*_args, **_kwargs):
    raise AssertionError("a detail page was read for a results list")


@pytest.fixture
def providers(monkeypatch):
    monkeypatch.setattr(search.steam, "search_store", lambda _q: [{"id": 1245620, "name": "ELDEN RING"}])
    monkeypatch.setitem(
        search.PROVIDERS, "GOG", search.ProviderSpec("GOG", "primary", lambda _c: True, lambda *_a: [])
    )


def test_a_light_search_reads_no_detail_pages(monkeypatch, providers) -> None:
    monkeypatch.setattr(search.steam, "get_app_details", _boom)
    monkeypatch.setattr(search.steam_tags, "fetch_player_tags", _boom)
    monkeypatch.setitem(
        search.PROVIDERS,
        "HowLongToBeat",
        search.ProviderSpec("HowLongToBeat", "enrichment", lambda _c: True, _boom),
    )
    out = search.search_game_metadata("elden ring", include_image_providers=False, light=True)
    assert [r["title"] for r in out["results"]] == ["ELDEN RING"]
    assert out["results"][0]["provider_id"] == "1245620"
    assert out["provider_errors"] == []
    assert "HowLongToBeat" not in out["providers"]


def test_a_full_search_still_reads_the_details(monkeypatch, providers) -> None:
    details = {
        "name": "ELDEN RING",
        "type": "game",
        "developers": ["FromSoftware"],
        "genres": [{"description": "RPG"}],
        "about_the_game": "A big world.",
    }
    monkeypatch.setattr(search.steam, "get_app_details", lambda _id: details)
    monkeypatch.setattr(search.steam_tags, "fetch_player_tags", lambda _id: [])
    monkeypatch.setitem(
        search.PROVIDERS,
        "HowLongToBeat",
        search.ProviderSpec("HowLongToBeat", "enrichment", lambda _c: True, lambda *_a: None),
    )
    out = search.search_game_metadata("elden ring", include_image_providers=False)
    first = out["results"][0]
    assert first["developer"] == "FromSoftware" and first["tags"] == ["RPG"]
    assert first["description"] == "A big world."
