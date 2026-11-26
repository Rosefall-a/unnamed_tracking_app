"""The quick game list does not wait for a slow provider: once one has answered,
the rest get a short grace period. The full lookup that fills a game in still
waits for every provider."""

import time

from src.features.metadata import search_utils
from src.features.metadata.games import search as games


def _fake(name: str, delay: float, title: str):
    def run(query, limit, ctx, existing):
        del query, limit, ctx, existing
        time.sleep(delay)
        return [
            {
                "provider": name,
                "provider_id": name,
                "title": title,
                "release_date": None,
            }
        ]

    return games.ProviderSpec(name, "primary", lambda ctx: True, run)


def _search(monkeypatch, light: bool, slow: float):
    monkeypatch.setitem(games.PROVIDERS, "Steam", _fake("Steam", 0.0, "Quick Game"))
    monkeypatch.setitem(games.PROVIDERS, "GOG", _fake("GOG", slow, "Slow Game"))
    monkeypatch.setattr(games, "GAME_LIST_GRACE_SECONDS", 0.3)
    search_utils._down_until.clear()
    started = time.monotonic()
    found = games.search_game_metadata(
        "game",
        8,
        preferences={**games.DEFAULT_PREFERENCES, "provider_order": ["Steam", "GOG"]},
        include_image_providers=False,
        light=light,
    )
    return found, time.monotonic() - started


def test_the_quick_list_does_not_wait_for_a_slow_provider(monkeypatch) -> None:
    found, took = _search(monkeypatch, light=True, slow=2.0)
    assert took < 1.5
    assert [r["title"] for r in found["results"]] == ["Quick Game"]
    # a provider that is only slow is not shown as an error when others answered
    assert found["provider_errors"] == []


def test_a_provider_that_answers_within_the_grace_is_kept(monkeypatch) -> None:
    found, _ = _search(monkeypatch, light=True, slow=0.1)
    assert sorted(r["title"] for r in found["results"]) == ["Quick Game", "Slow Game"]


def test_the_full_lookup_still_waits_for_every_provider(monkeypatch) -> None:
    found, took = _search(monkeypatch, light=False, slow=0.6)
    assert took >= 0.6
    assert sorted(r["title"] for r in found["results"]) == ["Quick Game", "Slow Game"]
