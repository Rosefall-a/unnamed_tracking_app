"""Tracks which metadata-sourced fields an admin has deliberately changed
on a Movie/TVShow/Anime row, so the "Apply metadata" search result button
(features/metadata/*/search.py's results, applied via each FormModal) can
skip re-filling them later instead of silently overwriting a manual fix."""

from typing import Any, Protocol

from fastapi import HTTPException

from src.core.auth import AuthenticatedActor


class _LockableEntity(Protocol):
    locked_fields: list[str]


def authorize_title_update(
    entity: _LockableEntity, updates: dict[str, Any], actor: AuthenticatedActor | None = None
) -> None:
    """Reject protected mutations before applying *any* part of an update."""
    if "locked_fields" in updates:
        raise HTTPException(403, "Use title_lock to manage title protection.")
    title_changed = "title" in updates and updates["title"] != getattr(entity, "title", None)
    if "title_lock" in updates or ("title" in (entity.locked_fields or []) and title_changed):
        if not isinstance(actor, AuthenticatedActor) or not actor.can_manage_protected_metadata:
            raise HTTPException(
                403, "An interactive application session is required to manage protected titles."
            )


def apply_updates_with_locking(
    entity: _LockableEntity,
    updates: dict[str, Any],
    lockable_fields: frozenset[str],
    *,
    actor: AuthenticatedActor | None = None,
) -> None:
    """Apply updates while tracking deliberately changed metadata fields.

    ``title_lock`` is an explicit override used by edit forms. When omitted,
    changing a title keeps the existing behaviour of locking it automatically.
    Passing ``True`` locks the title; passing ``False`` explicitly unlocks it.
    """
    authorize_title_update(entity, updates, actor)
    updates = dict(updates)
    title_lock = updates.pop("title_lock", None)

    locked = set(entity.locked_fields or [])
    for field, value in updates.items():
        if field in lockable_fields and value != getattr(entity, field):
            locked.add(field)
        setattr(entity, field, value)

    if title_lock is True:
        locked.add("title")
    elif title_lock is False:
        locked.discard("title")

    entity.locked_fields = sorted(locked)


def apply_metadata_updates(entity: _LockableEntity, updates: dict[str, Any]) -> set[str]:
    """Apply provider/import updates without changing locks or protected fields.

    Callers must load existing rows under a row lock before checking protection.
    A derived sort title must also stay unchanged when its title is protected.
    """
    locked = set(entity.locked_fields or [])
    if "title" in locked:
        locked.add("sort_title")
    changed = set()
    for field, value in updates.items():
        if field in locked or field in {"locked_fields", "title_lock"}:
            continue
        if value != getattr(entity, field, None):
            setattr(entity, field, value)
            changed.add(field)
    return changed
