from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.database.models.game import SCREENSHOT_NAME_MAX_LENGTH


class ScreenshotUpdate(BaseModel):
    """Payload for renaming a screenshot or replacing its tag set. Both optional.

    `tags` is a full replacement, given as tag names — unknown names are
    created (scoped to the current user) and reused if they already exist.
    """

    name: str | None = Field(default=None, min_length=1, max_length=SCREENSHOT_NAME_MAX_LENGTH)
    tags: list[str] | None = None


class ScreenshotTagRead(BaseModel):
    """A tag as attached to a screenshot."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class ScreenshotRead(BaseModel):
    """Screenshot metadata returned to clients. Use the /file endpoint for the image itself."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    name: str
    original_filename: str | None
    content_type: str | None
    tags: list[ScreenshotTagRead]
    file_size_bytes: int
    width: int | None
    height: int | None
    created_at: int = Field(description="Unix timestamp in seconds — also the upload date.")
    updated_at: int = Field(description="Unix timestamp in seconds when the screenshot was last updated.")


class ScreenshotTagUpdate(BaseModel):
    """Payload for renaming a tag."""

    name: str = Field(min_length=1, max_length=50)


class ScreenshotTagWithCount(BaseModel):
    """A tag plus how many screenshots currently use it, for tag-management UIs."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    screenshot_count: int
