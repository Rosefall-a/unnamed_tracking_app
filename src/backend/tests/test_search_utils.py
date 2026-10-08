"""A provider that is down must not hold up a search the others have answered."""

import time
from types import SimpleNamespace

from src.features.metadata.search_utils import run_providers


def _call_factory(slow_for: float = 0.0, slow_name: str = "slow", gives: list | None = None):
    def call(spec):
        if spec.name == slow_name:
            time.sleep(slow_for)  # stands in for a request waiting to give up
        return spec, gives if spec.name != slow_name else gives, None

    return call


def test_results_come_back_in_the_order_the_providers_were_given() -> None:
    specs = [SimpleNamespace(name="a"), SimpleNamespace(name="b")]
    out = run_providers(specs, _call_factory(gives=[{"title": "x"}]))
    assert [spec.name for spec, _, _ in out] == ["a", "b"]
    assert all(outcome == [{"title": "x"}] for _, outcome, _ in out)


def test_a_stalled_provider_is_given_up_on_once_another_has_results() -> None:
    specs = [SimpleNamespace(name="fast"), SimpleNamespace(name="slow")]
    started = time.monotonic()
    out = run_providers(specs, _call_factory(slow_for=4, gives=[{"title": "x"}]), deadline=10)
    assert time.monotonic() - started < 3, "the search waited for the stalled provider"
    assert out[0][1] == [{"title": "x"}]
    assert out[1][1] is None and out[1][2]


def test_with_no_results_the_deadline_is_what_ends_the_wait() -> None:
    specs = [SimpleNamespace(name="slow")]
    started = time.monotonic()
    out = run_providers(specs, _call_factory(slow_for=3, gives=[]), deadline=0.5)
    assert time.monotonic() - started < 2
    assert out[0][2]


def test_a_provider_that_is_down_reads_short_and_only_shows_when_nothing_answered() -> None:
    from src.features.metadata.search_utils import format_provider_error, visible_errors

    long = (
        "Could not reach Jikan: HTTPSConnectionPool(host='api.jikan.moe', port=443): Max retries "
        "exceeded with url: /v4/anime (Caused by NewConnectionError: Network is unreachable)"
    )
    message = format_provider_error("MyAnimeList", long)
    assert message == "MyAnimeList: could not be reached right now."
    assert visible_errors([message], have_results=True) == []
    assert visible_errors([message], have_results=False) == [message]


def test_rate_limiting_is_still_called_out_even_when_it_ran_out_of_retries() -> None:
    from src.features.metadata.search_utils import format_provider_error, visible_errors

    message = format_provider_error("Jikan", "Max retries exceeded: too many 429 error responses")
    assert "rate limited" in message
    assert visible_errors([message], have_results=True) == [message]


def test_the_same_search_twice_is_answered_from_memory_but_errors_are_not_kept() -> None:
    from src.features.metadata import search_utils

    search_utils._cache.clear()
    calls: list[int] = []

    def clean():
        calls.append(1)
        return {"results": [1], "provider_errors": []}

    assert search_utils.cached_search(("k",), clean) == search_utils.cached_search(("k",), clean)
    assert len(calls) == 1

    def failing():
        calls.append(1)
        return {"results": [], "provider_errors": ["x: could not be reached right now."]}

    search_utils.cached_search(("e",), failing)
    search_utils.cached_search(("e",), failing)
    assert len(calls) == 3


def test_a_provider_that_could_not_connect_is_skipped_for_a_while() -> None:
    from src.features.metadata import search_utils

    search_utils._down_until.clear()
    calls: list[str] = []

    def call(spec):
        calls.append(spec.name)
        if spec.name == "gone":
            return spec, None, "Could not reach Jikan: Network is unreachable"
        return spec, [{"title": "x"}], None

    specs = [SimpleNamespace(name="up"), SimpleNamespace(name="gone")]
    first = search_utils.run_providers(specs, call)
    second = search_utils.run_providers(specs, call)
    assert calls == ["up", "gone", "up"], "the unreachable provider was asked again"
    assert second[0][1] == [{"title": "x"}] and second[1][1] is None and second[1][2]
    search_utils._down_until.clear()
    assert first[1][2]


def test_a_provider_that_was_only_slow_is_not_marked_down() -> None:
    from src.features.metadata import search_utils

    search_utils._down_until.clear()

    def call(spec):
        if spec.name == "slow":
            time.sleep(2.5)
        return spec, [{"title": "x"}], None

    specs = [SimpleNamespace(name="fast"), SimpleNamespace(name="slow")]
    search_utils.run_providers(specs, call)
    assert "slow" not in search_utils._down_until
