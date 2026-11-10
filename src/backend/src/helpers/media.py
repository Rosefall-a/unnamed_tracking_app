"""Shared helpers for bulk screenshot/clip uploads — used both for a game's
own screenshots/clips folders and for the per-user "inbox" of unassigned
media (uploaded before being sorted into a game)."""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Literal

from fastapi import UploadFile

MediaKind = Literal["screenshot", "clip", "soundtrack"]

# \\w keeps letters of every language, so a name in Japanese survives; anything that
# means something in a path or an address does not
_SAFE_NAME = re.compile(r"[^\w.-]+")
_MAX_STEM = 200
_UPLOAD_CHUNK = 1024 * 1024
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".jfif", ".gif", ".webp", ".avif", ".bmp"}
_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".ogv"}
_AUDIO_EXTENSIONS = {".mp3", ".ogg", ".oga", ".opus", ".wav", ".flac", ".m4a", ".aac"}


def classify_media(content_type: str | None, filename: str) -> MediaKind | None:
    """Images become screenshots, videos become clips, audio becomes
    soundtrack — everything else is rejected.

    The extension decides. The content type is whatever the sender says, and the
    original extension is kept on the saved file and used to pick the type it is
    served as, so a page named x.html sent as image/png must not pass. A file
    that has no allowed extension is rejected whatever it claims to be."""
    del content_type
    ext = Path(filename).suffix.lower()
    if ext in _IMAGE_EXTENSIONS:
        return "screenshot"
    if ext in _VIDEO_EXTENSIONS:
        return "clip"
    if ext in _AUDIO_EXTENSIONS:
        return "soundtrack"
    return None


_SUBDIRS: dict[MediaKind, str] = {
    "screenshot": "screenshots",
    "clip": "clips",
    "soundtrack": "soundtrack",
}


def media_subdir(kind: MediaKind) -> str:
    return _SUBDIRS[kind]


def safe_filename(original_name: str) -> str:
    """Strip path separators and unsafe characters; prefix a short random id
    so two uploads with the same original name never collide."""
    name = Path(original_name).name
    name = _SAFE_NAME.sub("_", name) or "file"
    path = Path(name)
    if len(path.stem) > _MAX_STEM:
        name = path.stem[:_MAX_STEM] + path.suffix
    return f"{uuid.uuid4().hex[:8]}_{name}"


def save_media_bytes(data: bytes, dest_dir: Path, original_name: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / safe_filename(original_name)
    temporary = path.with_name(f".{path.name}.part")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    return path


class UploadTooLarge(Exception):
    """The file passed its limit while it was being saved."""


async def save_upload(
    file: UploadFile, dest_dir: Path, original_name: str, limit_bytes: int
) -> tuple[Path, int]:
    """Writes an upload to disk a piece at a time, so a clip or modpack of a few GB
    is never held in memory. It only takes its real name once it is all there."""
    if file.size is not None and file.size > limit_bytes:
        raise UploadTooLarge
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / safe_filename(original_name)
    temporary = path.with_name(f".{path.name}.part")
    size = 0
    try:
        with temporary.open("wb") as output:
            while chunk := await file.read(_UPLOAD_CHUNK):
                size += len(chunk)
                if size > limit_bytes:
                    raise UploadTooLarge
                output.write(chunk)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return path, size


def list_media(dir_path: Path) -> list[str]:
    if not dir_path.exists():
        return []
    # a name starting with a dot is an upload still being written
    return sorted(
        p.name for p in dir_path.iterdir() if p.is_file() and not p.name.startswith(".")
    )
