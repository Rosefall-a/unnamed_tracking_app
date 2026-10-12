"""Filling in what a movie is missing, from the provider's entry for it.

A movie added from the library's quick add used to be saved without its length
(and other details), so it showed no time. This looks each one up again and fills
in only what is empty: nothing already there is replaced, and a field the person
locked is left alone.
"""

from typing import Any

from src.database.models.movies import Movie
from src.features.metadata.search_utils import titles_match

# the movie's field, and whether the provider's value for it counts as "something"
_FIELDS = (
    "runtime_minutes",
    "description",
    "director",
    "writer",
    "studios",
    "countries",
    "genres",
    "backdrop_url",
)


def same_movie(movie: Movie, found: dict[str, Any]) -> bool:
    """The same title, and the same year when both know it: a remake with the same
    name must not lend its length to the original."""
    if not titles_match(movie.title, str(found.get("title") or "")):
        return False
    released = str(found.get("release_date") or "")
    return not (movie.release_date and released and released[:4] != str(movie.release_date.year))


def fill_empty_fields(movie: Movie, found: dict[str, Any]) -> bool:
    """Set each empty, unlocked field from `found`. True if anything was filled."""
    changed = False
    locked = movie.locked_fields or []
    for field in _FIELDS:
        value = found.get(field)
        if not value or field in locked:
            continue
        if getattr(movie, field):
            continue
        setattr(movie, field, value)
        changed = True
    return changed
