"""What people paste as their Steam profile, and a library Steam won't share."""

import pytest

from src.features.metadata.games import steam


@pytest.mark.parametrize(
    ("pasted", "expected"),
    [
        ("https://steamcommunity.com/id/gabelogannewell/", "gabelogannewell"),
        ("steamcommunity.com/id/someone", "someone"),
        ("https://steamcommunity.com/profiles/76561197960287930", "76561197960287930"),
        (
            "https://steamcommunity.com/profiles/76561197960287930/games/?tab=all",
            "76561197960287930",
        ),
        ("STEAM_0:0:11101", "76561197960287930"),
        ("STEAM_1:0:11101", "76561197960287930"),
        ("[U:1:22202]", "76561197960287930"),
        ("U:1:22202", "76561197960287930"),
        ("76561197960287930", "76561197960287930"),
        ("  vanity_name  ", "vanity_name"),
    ],
)
def test_profile_spellings(pasted, expected) -> None:
    assert steam.parse_steam_identifier(pasted) == expected


def test_a_profile_link_resolves_without_asking_steam(monkeypatch) -> None:
    def no_network(*_a, **_kw):
        raise AssertionError("a SteamID64 in the link needs no lookup")

    monkeypatch.setattr(steam.SESSION, "get", no_network)
    link = "https://steamcommunity.com/profiles/76561197960287930/"
    assert steam.resolve_steam_id(link, "key") == "76561197960287930"


def test_a_vanity_link_is_looked_up_by_its_name(monkeypatch) -> None:
    asked = {}

    class Reply:
        status_code = 200

        def json(self):
            return {"response": {"success": 1, "steamid": "76561197960287930"}}

    def fake_get(_url, params, **_kw):
        asked.update(params)
        return Reply()

    monkeypatch.setattr(steam.SESSION, "get", fake_get)
    assert (
        steam.resolve_steam_id("https://steamcommunity.com/id/gaben/", "k") == "76561197960287930"
    )
    assert asked["vanityurl"] == "gaben"


class _Owned:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def test_a_private_library_is_an_error_not_an_empty_one(monkeypatch) -> None:
    # Steam answers a private profile with an empty `response`
    monkeypatch.setattr(steam.SESSION, "get", lambda *_a, **_kw: _Owned(200, {"response": {}}))
    with pytest.raises(steam.SteamLibraryError, match="Game details to Public"):
        steam.get_owned_games("76561197960287930", "key")


def test_a_public_library_with_no_games_is_empty(monkeypatch) -> None:
    reply = _Owned(200, {"response": {"game_count": 0}})
    monkeypatch.setattr(steam.SESSION, "get", lambda *_a, **_kw: reply)
    assert steam.get_owned_games("76561197960287930", "key") == []


@pytest.mark.parametrize("status_code", [401, 403])
def test_a_rejected_key_says_so(monkeypatch, status_code) -> None:
    monkeypatch.setattr(steam.SESSION, "get", lambda *_a, **_kw: _Owned(status_code, {}))
    with pytest.raises(steam.SteamLibraryError, match="rejected the API key"):
        steam.get_owned_games("76561197960287930", "key")
