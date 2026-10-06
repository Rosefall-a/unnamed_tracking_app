"""Provider payload regressions without external API calls."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.features.metadata.games import search
from src.features.metadata.games.igdb import IGDBClient
from src.features.metadata.games.steam_grid_db import SteamGridDBClient


@pytest.mark.parametrize("image_type", ["hero", "heroes"])
def test_steamgrid_hero_aliases_return_matching_artwork(image_type):
    response = SimpleNamespace(
        status_code=200,
        json=lambda: {"success": True, "data": [{"id": 42, "type": "hero", "url": "art.png"}]},
    )
    session = Mock()
    session.request.return_value = response
    client = SteamGridDBClient("provider-test-key", session=session)
    images = client.get_game_images(123, image_type=image_type)
    assert [image.id for image in images] == [42]
    assert session.request.call_args.args[1].endswith("/heroes/game/123")


def test_igdb_search_normalizes_company_roles_artwork_and_series():
    token_response = SimpleNamespace(
        status_code=200, json=lambda: {"access_token": "test-token", "expires_in": 3600}
    )
    game_response = SimpleNamespace(
        status_code=200,
        json=lambda: [
            {
                "id": 7,
                "name": "Portal",
                "first_release_date": 1191888000,
                "cover": {"url": "//images.example/t_thumb/portal.jpg"},
                "involved_companies": [
                    {"company": {"name": "Valve"}, "developer": True, "publisher": True},
                    {"company": {"name": "Other"}, "developer": True},
                ],
                "franchises": [{"name": "Portal"}],
                "genres": [{"name": "Puzzle"}, {}],
            }
        ],
    )
    session = Mock()
    session.post.side_effect = [token_response, game_response]
    games = IGDBClient("test-client", "test-secret", session=session).search("Portal")
    assert games == [
        {
            "id": 7,
            "name": "Portal",
            "summary": None,
            "release_date": "2007-10-09",
            "developer": "Valve",
            "publisher": "Valve",
            "series": "Portal",
            "genres": ["Puzzle"],
            "cover_url": "https://images.example/t_cover_big/portal.jpg",
            "url": "https://www.igdb.com/games/7",
        }
    ]
    assert session.post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-token"


def test_search_keeps_provider_priority_and_enriches_after_partial_failure(monkeypatch):
    def primary(_query, _limit, _context, _existing):
        return [{"provider": "IGDB", "provider_id": "7", "title": "Portal™", "links": []}]

    def fallback(_query, _limit, _context, _existing):
        return [
            {
                "provider": "Steam",
                "provider_id": "400",
                "title": "portal",
                "description": "Provider description",
                "developer": "Valve",
                "links": [{"label": "Steam", "url": "https://example.test/portal"}],
            }
        ]

    def unavailable(_query, _limit, _context, _existing):
        raise RuntimeError("429 Too Many Requests")

    def enrich(_query, _limit, _context, existing):
        assert len(existing) == 1
        existing[0]["time_to_beat_hours"] = 3

    monkeypatch.setattr(
        search,
        "PROVIDERS",
        {
            name: search.ProviderSpec(name, kind, lambda _context: True, operation)
            for name, kind, operation in [
                ("IGDB", "primary", primary),
                ("GOG", "primary", unavailable),
                ("Steam", "primary", fallback),
                ("HowLongToBeat", "enrichment", enrich),
            ]
        },
    )
    result = search.search_game_metadata(
        "Portal",
        preferences={
            "provider_order": ["IGDB", "GOG", "Steam", "HowLongToBeat"],
            "steam_user_tags": False,
            "save_developer": False,
        },
        include_image_providers=False,
    )
    assert result["providers"] == ["IGDB", "Steam", "HowLongToBeat"]
    assert result["provider_errors"] == [
        "GOG: rate limited by the provider, try again in a few minutes."
    ]
    assert result["results"] == [
        {
            "provider": "IGDB",
            "provider_id": "7",
            "title": "Portal™",
            "links": [{"label": "Steam", "url": "https://example.test/portal"}],
            "description": "Provider description",
            "developer": None,
            "time_to_beat_hours": 3,
        }
    ]
