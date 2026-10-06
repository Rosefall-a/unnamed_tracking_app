"""Regression coverage for the public AniList relation graph."""

from types import SimpleNamespace
from unittest.mock import Mock

from src.features.metadata import rate_limit
from src.features.metadata.anime import anilist


def test_related_duology_is_reparented_without_failing_the_graph(monkeypatch):
    first = {"id": 2, "title": {"english": "First movie"}, "format": "MOVIE"}
    second = {"id": 3, "title": {"english": "Second movie"}, "format": "MOVIE"}
    nodes = {
        1: {
            "id": 1,
            "format": "TV",
            "title": {"english": "Series"},
            "relations": {
                "edges": [
                    {"relationType": "ALTERNATIVE", "node": second},
                    {"relationType": "ALTERNATIVE", "node": first},
                ]
            },
        },
        2: first,
        3: {
            **second,
            "relations": {"edges": [{"relationType": "PREQUEL", "node": first}]},
        },
    }
    session = Mock()
    session.post.side_effect = lambda _url, **kwargs: SimpleNamespace(
        status_code=200, json=lambda: {"data": {"Media": nodes[kwargs["json"]["variables"]["id"]]}}
    )
    monkeypatch.setattr(rate_limit, "throttle", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(anilist.time, "sleep", lambda _seconds: None)
    result = anilist.AniListClient(session=session).relations_chain_and_branches("Series", "1")
    assert [entry["id"] for entry in result["chain"]] == [1]
    assert [entry["id"] for entry in result["branches"]] == [2, 3]
    assert result["branches"][1]["anchor_id"] == 2
    assert result["branches"][1]["anchor_kind"] == "branch"
    assert result["branches"][1]["relation_label"] == "Sequel"
