from dataclasses import dataclass, field
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.core.auth import AuthenticatedActor

from src.features.metadata.locked_fields import apply_updates_with_locking


@dataclass
class Entity:
    title: str = "Original"
    description: str = "Original description"
    locked_fields: list[str] = field(default_factory=list)


def test_title_changes_are_locked_by_default() -> None:
    entity = Entity()

    apply_updates_with_locking(entity, {"title": "Manual title"}, frozenset({"title"}))

    assert entity.title == "Manual title"
    assert entity.locked_fields == ["title"]


def test_title_lock_can_be_explicitly_enabled_without_a_title_change() -> None:
    entity = Entity()

    apply_updates_with_locking(
        entity,
        {"title_lock": True},
        frozenset({"title"}),
        actor=AuthenticatedActor(uuid4(), "session"),
    )

    assert entity.title == "Original"
    assert entity.locked_fields == ["title"]


def test_title_lock_can_be_explicitly_disabled() -> None:
    entity = Entity(locked_fields=["title"])

    apply_updates_with_locking(
        entity,
        {"title_lock": False},
        frozenset({"title"}),
        actor=AuthenticatedActor(uuid4(), "session"),
    )

    assert entity.locked_fields == []


@pytest.mark.parametrize("actor_kind", ["api_key", "plugin"])
@pytest.mark.parametrize(
    "updates",
    [
        {"title": "Changed"},
        {"title_lock": True},
        {"title_lock": False},
        {"title": "Changed", "title_lock": False},
    ],
)
def test_protected_updates_fail_before_any_mutation(actor_kind, updates):
    entity = Entity(locked_fields=["title"])
    with pytest.raises(HTTPException) as exc:
        apply_updates_with_locking(
            entity,
            {"description": "Changed", **updates},
            frozenset({"title", "description"}),
            actor=AuthenticatedActor(uuid4(), actor_kind),
        )
    assert exc.value.status_code == 403
    assert entity.title == "Original"
    assert entity.description == "Original description"
    assert entity.locked_fields == ["title"]


def test_missing_actor_is_not_privileged():
    entity = Entity(locked_fields=["title"])
    with pytest.raises(HTTPException):
        apply_updates_with_locking(entity, {"title": "Changed"}, frozenset({"title"}))
