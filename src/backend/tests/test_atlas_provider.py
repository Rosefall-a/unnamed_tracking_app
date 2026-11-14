"""The Atlas metadata provider: its client, the address checks, and its place in a search."""

from __future__ import annotations

import socket
import uuid
from typing import Any

import pytest
import requests

from src.core.crypto import encrypt_secret
from src.database.models.user import User
from src.features.metadata.games import atlas as atlas_module
from src.features.metadata.games import search as search_module
from src.features.metadata.games.atlas import AtlasClient, AtlasError, normalize_base_url


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        body: Any = None,
        headers: dict[str, str] | None = None,
        json_error: bool = False,
    ) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}
        self._json_error = json_error

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status_code < 400

    def json(self) -> Any:
        if self._json_error:
            raise ValueError("not json")
        return self._body


class FakeSession:
    def __init__(self, *responses: FakeResponse | Exception) -> None:
        self.headers: dict[str, str] = {}
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        outcome = self.responses.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture(autouse=True)
def no_dns(monkeypatch):
    """Names resolve to a LAN address unless a test says otherwise."""
    monkeypatch.setattr(
        atlas_module.socket,
        "getaddrinfo",
        lambda host, port, **kwargs: [(socket.AF_INET, 0, 0, "", ("192.168.1.20", port))],
    )


def _client(*responses: FakeResponse | Exception) -> tuple[AtlasClient, FakeSession]:
    session = FakeSession(*responses)
    return AtlasClient("https://atlas.example.test", "token-1", session=session), session  # type: ignore[arg-type]


RECORD = {
    "id": "atlas:01HZZZZZZZZZZZZZZZZZZZZZZZ",
    "media_type": "game",
    "title": " Hades ",
    "description": "Escape the underworld.",
    "release_date": "2020-09-17",
    "developer": "Supergiant Games",
    "publisher": "Supergiant Games",
    "series": None,
    "age_rating": "T",
    "genres": ["Action", "", 7],
    "tags": ["Roguelike"],
    "themes": ["Mythology"],
    "features": ["Controller support"],
    "provider_ids": {"steam": 1145360},
    "an_unknown_future_field": {"nested": True},
}


# --- address checks ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://atlas.example.test", "https://atlas.example.test"),
        ("  https://atlas.example.test/  ", "https://atlas.example.test"),
        ("http://192.168.1.5:8080", "http://192.168.1.5:8080"),
        ("http://localhost:8000/", "http://localhost:8000"),
        ("https://example.test/atlas/", "https://example.test/atlas"),
        ("https://atlas.example.test/api/v2", "https://atlas.example.test"),
        ("https://example.test/atlas/api/v2/", "https://example.test/atlas"),
    ],
)
def test_normalize_base_url_keeps_a_plain_server_root(raw: str, expected: str) -> None:
    assert normalize_base_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "atlas.example.test",
        "ftp://atlas.example.test",
        "file:///etc/passwd",
        "https://user:pw@atlas.example.test",
        "https://atlas.example.test/?x=1",
        "https://atlas.example.test/#frag",
        "http://169.254.169.254/latest/meta-data",
        "http://[fe80::1]/",
        "http://0.0.0.0/",
        "http://metadata.google.internal/",
    ],
)
def test_normalize_base_url_refuses_unsafe_addresses(raw: str) -> None:
    with pytest.raises(AtlasError):
        normalize_base_url(raw)


def test_normalize_base_url_refuses_a_name_that_resolves_to_link_local(monkeypatch) -> None:
    monkeypatch.setattr(
        atlas_module.socket,
        "getaddrinfo",
        lambda host, port, **kwargs: [(socket.AF_INET, 0, 0, "", ("169.254.169.254", port))],
    )
    with pytest.raises(AtlasError):
        normalize_base_url("https://sneaky.example.test")


def test_normalize_base_url_lets_an_unresolvable_name_fail_later(monkeypatch) -> None:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise socket.gaierror("no such host")

    monkeypatch.setattr(atlas_module.socket, "getaddrinfo", fail)
    assert normalize_base_url("https://gone.example.test") == "https://gone.example.test"


def test_a_client_needs_both_an_address_and_a_token() -> None:
    with pytest.raises(AtlasError):
        AtlasClient("", "token")
    with pytest.raises(AtlasError):
        AtlasClient("https://atlas.example.test", "")


# --- search -----------------------------------------------------------------------


def test_search_sends_the_token_and_maps_a_record() -> None:
    client, session = _client(FakeResponse(body={"results": [RECORD]}))

    games = client.search("hades", limit=500)

    call = session.calls[0]
    assert call["url"] == "https://atlas.example.test/api/v2/games"
    assert call["params"] == {"q": "hades", "limit": 50, "type": "game"}
    assert call["headers"]["Authorization"] == "Bearer token-1"
    assert call["allow_redirects"] is False
    assert games == [
        {
            "id": "atlas:01HZZZZZZZZZZZZZZZZZZZZZZZ",
            "title": "Hades",
            "description": "Escape the underworld.",
            "release_date": "2020-09-17",
            "developer": "Supergiant Games",
            "publisher": "Supergiant Games",
            "series": None,
            "age_rating": "T",
            "genres": ["Action"],
            "tags": ["Roguelike", "Mythology"],
            "features": ["Controller support"],
            "url": "https://atlas.example.test/game/atlas:01HZZZZZZZZZZZZZZZZZZZZZZZ",
        }
    ]


def test_search_skips_records_it_cannot_use() -> None:
    movie = {**RECORD, "id": "atlas:movie", "media_type": "movie"}
    untitled = {**RECORD, "id": "atlas:untitled", "title": "  "}
    no_id = {k: v for k, v in RECORD.items() if k != "id"}
    client, _ = _client(FakeResponse(body={"results": [movie, untitled, no_id, "junk", RECORD]}))

    assert [game["id"] for game in client.search("hades")] == [RECORD["id"]]


def test_search_tolerates_a_missing_results_list_and_a_blank_query() -> None:
    client, session = _client(FakeResponse(body={"results": None}))
    assert client.search("hades") == []
    assert client.search("   ") == []
    assert len(session.calls) == 1


def test_a_record_id_of_an_unknown_shape_gets_no_link() -> None:
    client, _ = _client(FakeResponse(body={"results": [{**RECORD, "id": "other:1"}]}))
    assert client.search("hades")[0]["url"] is None


# --- errors -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (FakeResponse(401, {"detail": "Not authenticated"}), "rejected the token"),
        (FakeResponse(403, {"detail": "forbidden"}), "read scope"),
        (FakeResponse(429, {"detail": "slow"}, {"Retry-After": "12"}), "try again in 12s"),
        (FakeResponse(429, {"detail": "slow"}), "rate limiting"),
        (FakeResponse(404, {"error": {"code": "not_found", "message": "No such thing"}}), "No such thing"),
        (FakeResponse(500, {"detail": "boom"}), "boom"),
        (FakeResponse(502, "<html>bad gateway</html>", json_error=True), "(502)"),
        (FakeResponse(302, {}, {"Location": "http://elsewhere.test"}), "redirect"),
        (FakeResponse(200, json_error=True), "invalid JSON"),
        (FakeResponse(200, ["not", "an", "object"]), "unexpected response"),
        (requests.ConnectionError("refused"), "Could not reach Atlas"),
    ],
)
def test_search_reports_what_went_wrong(response: FakeResponse | Exception, message: str) -> None:
    client, _ = _client(response)
    with pytest.raises(AtlasError, match=message.replace("(", r"\(").replace(")", r"\)")):
        client.search("hades")


# --- validate ---------------------------------------------------------------------


def test_validate_checks_the_address_without_a_token_then_the_token() -> None:
    client, session = _client(
        FakeResponse(body={"name": "My Atlas", "contract": 1}), FakeResponse(body={"results": []})
    )

    assert client.validate() == {"validated": True, "node_name": "My Atlas"}
    assert session.calls[0]["url"].endswith("/api/v2/site")
    assert "Authorization" not in session.calls[0]["headers"]
    assert session.calls[1]["url"].endswith("/api/v2/games")
    assert session.calls[1]["headers"]["Authorization"] == "Bearer token-1"


def test_validate_fails_on_a_token_without_the_read_scope() -> None:
    client, _ = _client(FakeResponse(body={"name": "x"}), FakeResponse(403, {"detail": "no"}))
    with pytest.raises(AtlasError, match="read scope"):
        client.validate()


# --- in a metadata search ---------------------------------------------------------


def _user(*, connected: bool) -> User:
    return User(
        id=uuid.uuid4(),
        username="atlas_user",
        email="atlas_user@example.test",
        atlas_base_url="https://atlas.example.test" if connected else None,
        atlas_token=encrypt_secret("token-1") if connected else None,
    )


def test_atlas_only_runs_for_a_user_who_connected_one() -> None:
    spec = search_module.PROVIDERS["Atlas"]

    def ctx(user: User | None) -> search_module.ProviderContext:
        return search_module.ProviderContext(user=user, steamgriddb_api_key=None)

    assert spec.available(ctx(_user(connected=True)))
    assert not spec.available(ctx(_user(connected=False)))
    assert not spec.available(ctx(None))


def test_atlas_results_fill_a_search_result(monkeypatch) -> None:
    seen: dict[str, Any] = {}

    class StubClient:
        def __init__(self, base_url: str, token: str) -> None:
            seen["base_url"], seen["token"] = base_url, token

        def search(self, query: str, limit: int) -> list[dict[str, Any]]:
            seen["query"], seen["limit"] = query, limit
            return [
                {
                    "id": "atlas:A",
                    "title": "Hades",
                    "description": "Escape the underworld.",
                    "release_date": "2020-09-17",
                    "developer": "Supergiant Games",
                    "publisher": "Supergiant Games",
                    "series": None,
                    "age_rating": "T",
                    "genres": ["Action"],
                    "tags": ["Roguelike"],
                    "features": ["Controller support"],
                    "url": "https://atlas.example.test/game/atlas:A",
                }
            ]

    monkeypatch.setattr(search_module, "AtlasClient", StubClient)
    ctx = search_module.ProviderContext(user=_user(connected=True), steamgriddb_api_key=None)

    [result] = search_module._run_atlas("hades", 5, ctx, [])

    assert seen == {
        "base_url": "https://atlas.example.test",
        "token": "token-1",
        "query": "hades",
        "limit": 5,
    }
    assert result["provider"] == "Atlas"
    assert result["provider_id"] == "atlas:A"
    assert result["release_date"] == "2020-09-17"
    assert result["tags"] == ["Action", "Roguelike"]
    assert result["features"] == ["Controller support"]
    assert result["links"] == [{"label": "Atlas", "url": "https://atlas.example.test/game/atlas:A"}]
    assert result["key_art_url"] is None  # data providers never contribute art


def test_a_full_search_uses_atlas_and_reports_its_failure_without_sinking_the_search(
    monkeypatch,
) -> None:
    class BrokenClient:
        def __init__(self, base_url: str, token: str) -> None:
            pass

        def search(self, query: str, limit: int) -> list[dict[str, Any]]:
            raise AtlasError("Atlas rejected the token.")

    monkeypatch.setattr(search_module, "AtlasClient", BrokenClient)
    outcome = search_module.search_game_metadata(
        "hades",
        preferences={"provider_order": ["Atlas"], "image_provider_order": []},
        user=_user(connected=True),
        include_image_providers=False,
    )

    assert outcome["providers"] == []
    assert outcome["results"] == []
    assert outcome["provider_errors"] == ["Atlas: Atlas rejected the token."]


def test_atlas_is_a_data_provider_and_ordered_last_by_default() -> None:
    assert "Atlas" in search_module.DATA_PROVIDER_NAMES
    assert "Atlas" not in search_module.IMAGE_PROVIDER_NAMES
    assert search_module.DEFAULT_PROVIDER_ORDER[-1] == "Atlas"
