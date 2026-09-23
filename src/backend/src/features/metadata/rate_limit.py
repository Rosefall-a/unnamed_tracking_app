"""A tiny process-wide throttle shared by every provider client.

Several background loops (episode refresh, airing check, metadata heal)
each walk the whole library and call the same external APIs, and they
all fire their first pass immediately on app startup — with no shared
throttle, that means several loops can hit AniList/Jikan in the same
instant, and each one's own per-call retry/backoff (see anilist.py,
jikan.py) doesn't know about the others, so the herd just collides again
on the next attempt. This keeps a minimum gap between *any* two calls to
the same provider, no matter which loop or thread makes them, so a show
stuck behind a 429 gets healed on the next pass instead of indefinitely
losing that race every cycle.
"""

import threading
import time

_locks: dict[str, threading.Lock] = {}
_last_call: dict[str, float] = {}
_registry_lock = threading.Lock()


def throttle(provider: str, min_interval_seconds: float) -> None:
    """Blocks (if needed) so at least `min_interval_seconds` has passed
    since the last call tagged with this `provider` name, across every
    client instance and every thread in the process."""
    with _registry_lock:
        lock = _locks.setdefault(provider, threading.Lock())
    with lock:
        now = time.monotonic()
        elapsed = now - _last_call.get(provider, 0.0)
        wait = min_interval_seconds - elapsed
        if wait > 0:
            time.sleep(wait)
        _last_call[provider] = time.monotonic()
