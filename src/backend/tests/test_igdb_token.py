"""IGDB's Twitch token is shared by every client with the same credentials."""

from typing import Any

import pytest

from src.features.metadata.games import igdb


class Reply:
    def __init__(self, status: int, data: Any) -> None:
        self.status_code = status
        self._data = data
        self.text = str(data)

    def json(self) -> Any:
        return self._data


class FakeTwitch:
    def __init__(self) -> None:
        self.tokens_issued = 0
        self.valid: set[str] = set()
        self.searches = 0

    def post(self, url: str, **kw: Any) -> Reply:
        if url == igdb.IGDBClient.TOKEN_URL:
            self.tokens_issued += 1
            token = f"token-{self.tokens_issued}"
            self.valid.add(token)
            return Reply(200, {"access_token": token, "expires_in": 5_000_000})
        self.searches += 1
        if kw["headers"]["Authorization"].removeprefix("Bearer ") not in self.valid:
            return Reply(401, {"message": "invalid token"})
        return Reply(200, [{"id": 1, "name": "Hades", "collection": {"name": "Hades"}}])


@pytest.fixture(autouse=True)
def fresh_tokens(monkeypatch):
    monkeypatch.setattr(igdb, "_TOKENS", {})


def test_clients_share_one_token() -> None:
    twitch = FakeTwitch()
    for _ in range(5):
        client = igdb.IGDBClient("id", "secret", session=twitch)  # type: ignore[arg-type]
        assert client.search("Hades")[0]["series"] == "Hades"
    assert twitch.tokens_issued == 1
    assert twitch.searches == 5


def test_other_credentials_get_their_own_token() -> None:
    twitch = FakeTwitch()
    igdb.IGDBClient("id", "secret", session=twitch).search("Hades")  # type: ignore[arg-type]
    igdb.IGDBClient("id2", "secret2", session=twitch).search("Hades")  # type: ignore[arg-type]
    assert twitch.tokens_issued == 2


def test_a_revoked_token_is_replaced_and_the_search_retried() -> None:
    twitch = FakeTwitch()
    igdb.IGDBClient("id", "secret", session=twitch).search("Hades")  # type: ignore[arg-type]
    twitch.valid.clear()  # Twitch revoked it
    results = igdb.IGDBClient("id", "secret", session=twitch).search("Hades")  # type: ignore[arg-type]
    assert results[0]["name"] == "Hades"
    assert twitch.tokens_issued == 2
    # and the replacement is what the next client uses
    igdb.IGDBClient("id", "secret", session=twitch).search("Hades")  # type: ignore[arg-type]
    assert twitch.tokens_issued == 2
