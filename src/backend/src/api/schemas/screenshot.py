from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.database.models.game import SCREENSHOT_NAME_MAX_LENGTH


class ScreenshotUpdate(BaseModel):
    """Payload for renaming a screenshot or editing its tags. Both optional."""

    name: str | None = Field(default=None, min_length=1, max_length=SCREENSHOT_NAME_MAX_LENGTH)
    tags: list[str] | None = None


class ScreenshotRead(BaseModel):
    """Screenshot metadata returned to clients. Use the /file endpoint for the image itself."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    name: str
    original_filename: str | None
    content_type: str | None
    tags: list[str]
    file_size_bytes: int
    width: int | None
    height: int | None
    created_at: int = Field(description="Unix timestamp in seconds — also the upload date.")
    updated_at: int = Field(description="Unix timestamp in seconds when the screenshot was last updated.")
