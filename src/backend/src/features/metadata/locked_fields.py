"""Tracks which metadata-sourced fields an admin has deliberately changed
on a Movie/TVShow/Anime row, so the "Apply metadata" search result button
(features/metadata/*/search.py's results, applied via each FormModal) can
skip re-filling them later instead of silently overwriting a manual fix."""

from typing import Any, Protocol


class _LockableEntity(Protocol):
    locked_fields: list[str]


def drop_nulls_for_required(entity: Any, updates: dict[str, Any]) -> dict[str, Any]:
    """A PATCH that sends null for a column that cannot be null means "leave it",
    not "clear it": writing the null would fail in the database with a 500. The
    columns that can hold null (a date, a note, a rating) are cleared as asked."""
    table = getattr(entity, "__table__", None)
    if table is None:  # not a database row (a stand-in in a test): nothing to look up
        return updates
    columns = table.columns
    return {
        field: value
        for field, value in updates.items()
        if value is not None or field not in columns or columns[field].nullable
    }


def apply_updates_with_locking(
    entity: _LockableEntity,
    updates: dict[str, Any],
    lockable_fields: frozenset[str],
) -> None:
    """Applies `updates` onto `entity`. Any field in `lockable_fields`
    whose value actually changes is added to `entity.locked_fields`."""
    locked = set(entity.locked_fields)
    updates = drop_nulls_for_required(entity, updates)
    for field, value in updates.items():
        if field in lockable_fields and value != getattr(entity, field):
            locked.add(field)
        setattr(entity, field, value)
    entity.locked_fields = sorted(locked)
