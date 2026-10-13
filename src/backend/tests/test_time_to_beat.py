"""Time to beat comes from IGDB; HowLongToBeat refuses automated requests."""

from src.features.metadata.games import search
from src.features.metadata.games.igdb import IGDBClient


class _Reply:
    def __init__(self, payload, status=200):
        self._payload, self.status_code, self.text = payload, status, ""

    def json(self):
        return self._payload


def _client(monkeypatch, rows):
    client = IGDBClient("id", "secret")
    monkeypatch.setattr(client, "_authenticate", lambda: "token")
    monkeypatch.setattr(
        IGDBClient, "search", lambda _s, _q, limit=8: [{"id": 7, "name": "Elden Ring"}]
    )
    monkeypatch.setattr(client, "_post_games", lambda _body, endpoint="games": _Reply(rows))
    return client


def test_the_main_story_figure_is_used_in_hours(monkeypatch) -> None:
    client = _client(monkeypatch, [{"normally": 198_000, "hastily": 144_000, "completely": 360_000}])
    assert client.time_to_beat("Elden Ring") == 55.0


def test_a_rushed_figure_is_the_fallback(monkeypatch) -> None:
    client = _client(monkeypatch, [{"hastily": 36_000}])
    assert client.time_to_beat("Elden Ring") == 10.0


def test_no_figure_is_none(monkeypatch) -> None:
    assert _client(monkeypatch, []).time_to_beat("Elden Ring") is None


def _ctx():
    return search.ProviderContext(user=None, steamgriddb_api_key=None, igdb_client_id="a", igdb_client_secret="b")


def test_howlongtobeat_is_asked_first(monkeypatch) -> None:
    every_time = {
        "time_to_beat_hours": 60.1,
        "time_to_beat_extras_hours": 101.4,
        "time_to_beat_completionist_hours": 136.2,
        "time_to_beat_all_hours": 105.6,
    }
    monkeypatch.setattr(search.HLTBClient, "find_times", lambda _s, title: dict(every_time))

    def boom(*_a, **_k):
        raise AssertionError("IGDB was called")

    monkeypatch.setattr(IGDBClient, "play_times", boom)
    results = [{"title": "Elden Ring"}, {"title": "Other", "time_to_beat_hours": 3.0}]
    search._run_hltb("elden ring", 8, _ctx(), results)
    assert {k: results[0][k] for k in every_time} == every_time  # all four, not just the main story
    assert results[1]["time_to_beat_hours"] == 3.0


def test_igdb_fills_in_when_howlongtobeat_cannot_be_reached(monkeypatch) -> None:
    calls = []

    def down(_s, title):
        calls.append(title)
        raise search.HLTBError("blocked")

    monkeypatch.setattr(search.HLTBClient, "find_times", down)
    monkeypatch.setattr(IGDBClient, "play_times", lambda _s, title: {"time_to_beat_hours": 12.5})
    results = [{"title": "A"}, {"title": "B"}]
    search._run_hltb("a", 8, _ctx(), results)
    assert [r["time_to_beat_hours"] for r in results] == [12.5, 12.5]
    assert calls == ["A"]  # not asked again once it is known to be down


def test_the_client_gets_a_token_and_retries_once_when_it_expires() -> None:
    from src.features.metadata.games.hltb import HLTBClient

    class Reply:
        def __init__(self, status, payload):
            self.status_code, self._p = status, payload

        def json(self):
            return self._p

    class Session:
        def __init__(self):
            self.headers = {}
            self.tokens = iter(["old", "new"])
            self.searches = []

        def get(self, url, **_k):
            if url.endswith("/init"):
                return Reply(200, {"token": next(self.tokens)})
            return Reply(200, {})  # the home page, visited first for its cookie

        def post(self, url, json=None, headers=None, **_k):
            self.searches.append(headers["x-auth-token"])
            if headers["x-auth-token"] == "old":
                return Reply(403, {})
            return Reply(
                200,
                {
                    "data": [
                        {
                            "game_id": 1,
                            "game_name": "Elden Ring",
                            "comp_main": 216_517,
                            "comp_plus": 365_069,
                            "comp_100": 490_350,
                            "comp_all": 380_166,
                        }
                    ]
                },
            )

    session = Session()
    client = HLTBClient(session=session)
    assert client.find_times("Elden Ring") == {
        "time_to_beat_hours": 60.1,
        "time_to_beat_extras_hours": 101.4,
        "time_to_beat_completionist_hours": 136.2,
        "time_to_beat_all_hours": 105.6,
    }
    assert client.find_time_to_beat("Elden Ring") == 60.1
    assert session.searches[:2] == ["old", "new"]
