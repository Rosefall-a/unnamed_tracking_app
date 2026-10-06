"""Explicit title protection for the four library update operations."""

from pydantic import BaseModel, Field, StrictBool


class TitleProtectionUpdate(BaseModel):
    """Only fields supplied by the caller are applied by update routes."""

    title_lock: StrictBool = Field(
        default=False,
        description=(
            "Omit to preserve protection and automatic locking on manual edits. "
            "True protects the title; false removes protection. "
            "Requires an authenticated interactive application session."
        ),
    )
