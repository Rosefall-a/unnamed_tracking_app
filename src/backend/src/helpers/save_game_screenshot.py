from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from PIL import Image

DATA_ROOT = Path("/data/users")

# Screenshots are stored as-is (no resizing) — this just guards against
# obviously-wrong uploads.
MAX_SCREENSHOT_BYTES = 25 * 1024 * 1024

_EXTENSION_BY_CONTENT_TYPE: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
}


def screenshots_dir(user_id: UUID | str, folder_name: str) -> Path:
    """Path to a game's screenshots directory. Assumes create_game_folder() already ran."""
    return DATA_ROOT / str(user_id) / "games" / folder_name / "screenshots"


def screenshot_file_path(user_id: UUID | str, folder_name: str, screenshot_id: UUID | str, extension: str) -> Path:
    return screenshots_dir(user_id, folder_name) / f"{screenshot_id}{extension}"


def derive_extension(original_filename: str | None, content_type: str | None) -> str:
    """Prefer the uploaded filename's extension, fall back to content-type, then a generic default."""
    if original_filename:
        suffix = Path(original_filename).suffix.lower()
        if suffix and len(suffix) <= 10:
            return suffix

    if content_type:
        mapped = _EXTENSION_BY_CONTENT_TYPE.get(content_type.split(";", 1)[0].strip().lower())
        if mapped:
            return mapped

    return ".png"


def derive_screenshot_name(explicit_name: str | None, original_filename: str | None) -> str:
    """Resolve the display name for a new screenshot.

    Priority: an explicitly given name > the original upload filename (without its
    extension) > "<upload date>-<short unique id>" as a last resort.
    """
    if explicit_name and explicit_name.strip():
        return explicit_name.strip()

    if original_filename and original_filename.strip():
        stem = Path(original_filename.strip()).stem.strip()
        if stem:
            return stem

    today = date.today().isoformat()
    return f"{today}-{uuid4().hex[:8]}"


def validate_and_measure_image(image_bytes: bytes) -> tuple[int, int]:
    """Confirm the bytes are a real, openable image and return its (width, height)."""
    with Image.open(BytesIO(image_bytes)) as img:
        img.verify()
    # verify() leaves the file unusable for further reads — reopen to read the size.
    with Image.open(BytesIO(image_bytes)) as img:
        return img.size


def save_screenshot_file(
    image_bytes: bytes,
    user_id: UUID | str,
    folder_name: str,
    screenshot_id: UUID | str,
    extension: str,
) -> Path:
    """Persist screenshot bytes to disk unchanged (no resizing/re-encoding)."""
    output_dir = screenshots_dir(user_id, folder_name)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = screenshot_file_path(user_id, folder_name, screenshot_id, extension)
    output_path.write_bytes(image_bytes)
    return output_path
