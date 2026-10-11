"""Shared helpers for metadata provider search implementations."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any, TypeVar

S = TypeVar("S")
# how long a results list waits for any one provider
SEARCH_DEADLINE_SECONDS = 5.0
# once a provider has results, how much longer the others are waited for
GRACE_SECONDS = 0.8
# a provider that could not be connected to is left out of searches for this long,
# so a service that is down costs nothing after the first time
DOWN_SECONDS = 60.0
_down_until: dict[str, float] = {}
_CONNECT_WORDS = ("could not reach", "max retries", "unreachable", "connection")


def run_providers(
    specs: list[S],
    call: Callable[[S], tuple[S, list[dict[str, Any]] | None, str | None]],
    deadline: float = SEARCH_DEADLINE_SECONDS,
) -> list[tuple[S, list[dict[str, Any]] | None, str | None]]:
    """Run every provider at once and return what each gave, in the order given.
    A provider that has not answered in time is reported as timed out and left to
    finish on its own. One that is down can take 15 s to give up, so once any
    provider has results the rest get only a short grace period, and one that
    could not be connected to is skipped for a minute afterwards."""
    started = time.monotonic()
    names = {id(spec): str(getattr(spec, "name", id(spec))) for spec in specs}
    live = [spec for spec in specs if _down_until.get(names[id(spec)], 0.0) <= started]
    executor = ThreadPoolExecutor(max_workers=max(1, len(live)))

    def guarded(spec: S) -> tuple[S, list[dict[str, Any]] | None, str | None]:
        # noted when it finishes, even if the search has already gone on without it
        outcome = call(spec)
        if any(word in (outcome[2] or "").lower() for word in _CONNECT_WORDS):
            _down_until[names[id(spec)]] = time.monotonic() + DOWN_SECONDS
        return outcome

    futures = [(spec, executor.submit(guarded, spec)) for spec in live]
    end = started + deadline
    pending = {future for _, future in futures}
    while pending and time.monotonic() < end:
        done, pending = wait(pending, timeout=end - time.monotonic(), return_when=FIRST_COMPLETED)
        if any(future.result()[1] for future in done):
            end = min(end, time.monotonic() + GRACE_SECONDS)
    answers: dict[int, tuple[S, list[dict[str, Any]] | None, str | None]] = {}
    for spec, future in futures:
        if future.done():
            answers[id(spec)] = future.result()
        else:
            answers[id(spec)] = (spec, None, "did not answer in time")
    executor.shutdown(wait=False)
    return [
        answers.get(id(spec), (spec, None, "was unreachable a moment ago")) for spec in specs
    ]


_UNREACHABLE_WORDS = ("could not reach", "max retries", "unreachable", "timed out", "did not answer")
UNREACHABLE_SUFFIX = "could not be reached right now."


def visible_errors(errors: list[str], have_results: bool) -> list[str]:
    """A provider that is down is only worth mentioning when nothing else answered:
    if the search found results, the warning is just noise."""
    if not have_results:
        return errors
    return [e for e in errors if not e.endswith(UNREACHABLE_SUFFIX)]


_cache: dict[tuple, tuple[float, Any]] = {}
CACHE_SECONDS = 120.0
_CACHE_ITEMS = 64


def cached_search(key: tuple, search: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """The same search asked again within a couple of minutes (retyping, going
    back, reopening the dialog) is answered from memory. Only clean answers are
    kept: one with a provider error is asked again."""
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    value = search()
    if not value.get("provider_errors"):
        if len(_cache) >= _CACHE_ITEMS:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (time.monotonic(), value)
    return value


def format_provider_error(name: str, message: str) -> str:
    """Turn provider exceptions into a concise, user-facing message."""
    lowered = message.lower()
    # rate limiting first: a retry error that ran out because of 429s mentions both
    if "429" in message or "rate limit" in lowered or "too many requests" in lowered:
        return f"{name}: rate limited by the provider, try again in a few minutes."
    if any(word in lowered for word in _UNREACHABLE_WORDS):
        return f"{name}: {UNREACHABLE_SUFFIX}"
    return f"{name}: {message}"


def titles_match(first: str, second: str) -> bool:
    """Compare titles while ignoring case, punctuation, and whitespace."""
    normalize = lambda value: "".join(char.lower() for char in value if char.isalnum())
    normalized_first = normalize(first)
    normalized_second = normalize(second)
    return bool(normalized_first) and normalized_first == normalized_second


def merge_search_result(
    results: list[dict[str, Any]],
    candidate: dict[str, Any],
    *,
    ignored_fields: frozenset[str] = frozenset({"provider", "provider_id", "title"}),
) -> None:
    """Merge a provider result into an existing title or append it.

    Provider-specific identity fields are never overwritten. Empty values in
    an existing result are filled from later providers when available.
    """
    for existing in results:
        if not titles_match(existing["title"], candidate["title"]):
            continue

        for key, value in candidate.items():
            if key in ignored_fields:
                continue
            if not existing.get(key) and value:
                existing[key] = value
        return

    results.append(candidate)
