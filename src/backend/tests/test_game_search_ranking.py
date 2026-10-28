"""The closest title comes first, whichever store answered first."""

from src.features.metadata.games.search import _rank_by_relevance, _relevance


def _titles(results):
    return [r["title"] for r in results]


def test_an_exact_title_beats_looser_matches_from_an_earlier_provider() -> None:
    results = [
        {"title": "Elden Ring Nightreign Collector's Edition"},
        {"title": "Elden Ring: Shadow of the Erdtree"},
        {"title": "ELDEN RING"},
    ]
    _rank_by_relevance(results, "elden ring")
    assert _titles(results)[0] == "ELDEN RING"


def test_ties_keep_the_provider_order() -> None:
    results = [{"title": "Hades"}, {"title": "hades"}, {"title": "Hades II"}]
    _rank_by_relevance(results, "hades")
    assert _titles(results) == ["Hades", "hades", "Hades II"]


def test_every_word_beats_a_partial_match() -> None:
    assert _relevance("The Witcher 3: Wild Hunt", "witcher hunt") == 2
    assert _relevance("Witcher Tales", "witcher hunt") == 4
    assert _relevance("Anything", "") == 4
