"""Keeps a season's two records of "what I've watched" in agreement.

A season has a progress counter (`episodes_watched`, what the library list
shows and what its "+" button moves) and each episode row has its own
`watched` flag (what the title page's episode list shows). They used to be
independent, so checking off episodes on a title page never moved the
number in the library, and pressing "+" in the library never ticked an
episode. These helpers make every change to one update the other.

The counter is a COUNT of watched episodes. Old data recorded progress
only in the counter (Naruto: 220, no episode flagged), so a counter can
be larger than the number of flagged episodes; the difference is progress
not yet represented by flags ("unbacked"), and it is assumed to be the
lowest-numbered unflagged episodes, the way progress is normally made.

- before an episode flag changes, that unbacked progress is turned into
  flags (`materialize_progress`), so the list shows what the library was
  already counting and the change can't silently erase it
- after a flag change the counter is recomputed as flags plus whatever
  progress has no episode row at all (`counter_from_flags`)
- when the counter is set directly, that many episodes are flagged from
  the lowest number up, and if it went down, the highest flags are cleared
  (`apply_counter`)"""

from collections.abc import Iterable
from typing import Any


def unbacked_progress(season: Any, extra: Iterable[Any] = ()) -> int:
    """Progress the counter holds that no episode flag accounts for. `extra`
    is episode rows just created and not yet in `season.episodes`."""
    flagged = sum(1 for e in [*season.episodes, *extra] if e.watched)
    return max(0, (season.episodes_watched or 0) - flagged)


def materialize_progress(season: Any, extra: Iterable[Any] = ()) -> int:
    """Flags the lowest-numbered unflagged episodes to cover unbacked
    progress. Returns how much progress is left over that has no episode
    row to hold it (a season tracked by number before its episode list
    existed), which stays in the counter. Call it with `extra` right after
    creating a season's episode rows, so a show imported by number alone
    (a MAL list) shows those episodes as watched once they exist."""
    extra = list(extra)
    remaining = unbacked_progress(season, extra)
    for episode in sorted([*season.episodes, *extra], key=lambda e: e.episode_number):
        if remaining <= 0:
            break
        if not episode.watched:
            episode.watched = True
            remaining -= 1
    return remaining


def counter_from_flags(season: Any, without_row: int) -> None:
    """The counter after a flag change: flagged episodes plus the progress
    that never had a row."""
    season.episodes_watched = sum(1 for e in season.episodes if e.watched) + without_row


def apply_counter(season: Any, new_counter: int) -> None:
    """Called after `episodes_watched` was set directly: exactly that many
    episodes end up flagged. Raising it flags the lowest-numbered unflagged
    ones; lowering it clears the highest-numbered flagged ones."""
    episodes = sorted(season.episodes, key=lambda e: e.episode_number)
    flagged = [e for e in episodes if e.watched]
    if new_counter > len(flagged):
        need = new_counter - len(flagged)
        for episode in episodes:
            if need <= 0:
                break
            if not episode.watched:
                episode.watched = True
                need -= 1
    elif new_counter < len(flagged):
        for episode in reversed(flagged):
            if len(flagged) <= new_counter:
                break
            episode.watched = False
            flagged.remove(episode)


def finish_season(season: Any) -> int | None:
    """Every episode of a finished season counts as watched. Returns how many were
    newly marked, or None when nobody knows how many episodes it has."""
    total = season.episode_count
    if not total:
        return None
    watched = season.episodes_watched or 0
    if watched >= total:
        return 0
    season.episodes_watched = total
    apply_counter(season, total)
    return total - watched


def finish_seasons(
    seasons: Iterable[Any], finished: Any, keep: Iterable[Any] = ()
) -> tuple[int, int]:
    """Marks a whole show finished: every season's episodes, and each season's own
    status unless it already says something in `keep` (Favorite). Returns how many
    episodes were newly marked and how many seasons have no episode count."""
    marked = unknown = 0
    kept = set(keep)
    for season in seasons:
        newly = finish_season(season)
        if newly is None:
            unknown += 1
            continue
        marked += newly
        if season.status not in kept:
            season.status = finished
    return marked, unknown
