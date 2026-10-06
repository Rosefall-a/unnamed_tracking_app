"""Work out when a screenshot or clip was really taken.

A file's own "modified" date is often wrong for this: copying, syncing or
unzipping gives every file the day you moved it. So the date is found from the
most trustworthy place that has one, in this order:

1. the file's own data: photo data (EXIF or a PNG creation time) or a video's
   creation time, written by the camera or the capture tool
2. the file name, since Steam, PlayStation, Xbox, NVIDIA and most capture tools
   put the capture time in it (20260515191011_1.jpg, Screenshot 2026-05-15 19-10-11)
3. the file's modified date, as the browser reports it
4. the moment it was uploaded

The source is stored with the date so the app can say where it came from and
the user can tell a guess from a fact. Times with no zone are kept as UTC.
"""

from __future__ import annotations

import io
import re
import struct
import time
from calendar import timegm
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Literal

from PIL import ExifTags, Image, UnidentifiedImageError

DateSource = Literal["photo", "video", "filename", "file", "uploaded", "manual", "achievement"]

# an earlier "year" than this is a counter or a version number, not a date
_MIN_YEAR = 1995
_FUTURE_SLACK = 24 * 3600

# 2026-05-15 19-10-11, 20260515_191011, 2026.05.15T19:10:11 and the like
_FULL = re.compile(
    r"(?<!\d)(?P<y>(?:19|20)\d{2})[-_.]?(?P<mo>[01]\d)[-_.]?(?P<d>[0-3]\d)"
    r"[-_ T.]?(?P<h>[0-2]\d)[-_.:]?(?P<mi>[0-5]\d)[-_.:]?(?P<s>[0-5]\d)(?!\d)"
)
_DAY = re.compile(r"(?<!\d)(?P<y>(?:19|20)\d{2})[-_.](?P<mo>[01]\d)[-_.](?P<d>[0-3]\d)(?!\d)")


def _to_unix(y: int, mo: int, d: int, h: int = 0, mi: int = 0, s: int = 0) -> int | None:
    try:
        value = timegm(datetime(y, mo, d, h, mi, s).timetuple())
    except ValueError:
        return None
    return value


def _sane(value: int | None, now: float) -> int | None:
    if value is None:
        return None
    if value > now + _FUTURE_SLACK:
        return None
    if datetime.fromtimestamp(value, UTC).year < _MIN_YEAR:
        return None
    return value


def from_filename(name: str, now: float | None = None) -> int | None:
    now = time.time() if now is None else now
    stem = Path(name).stem
    match = _FULL.search(stem)
    if match:
        parts = [int(match.group(k)) for k in ("y", "mo", "d", "h", "mi", "s")]
        found = _sane(_to_unix(*parts), now)
        if found is not None:
            return found
    match = _DAY.search(stem)
    if match:
        parts = [int(match.group(k)) for k in ("y", "mo", "d")]
        return _sane(_to_unix(*parts), now)
    return None


def _parse_exif_text(text: object) -> int | None:
    if not isinstance(text, str):
        return None
    try:
        parsed = datetime.strptime(text.strip()[:19], "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    return timegm(parsed.timetuple())


def _parse_png_time(text: object) -> int | None:
    """PNG's own "Creation Time" text chunk: RFC 1123 or ISO 8601."""
    if not isinstance(text, str):
        return None
    try:
        parsed = parsedate_to_datetime(text.strip())
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(text.strip())
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return timegm(parsed.timetuple())
    return int(parsed.timestamp())


def from_photo_data(data: bytes, now: float | None = None) -> int | None:
    now = time.time() if now is None else now
    try:
        with Image.open(io.BytesIO(data)) as image:
            exif = image.getexif()
            original = exif.get_ifd(ExifTags.IFD.Exif).get(36867)  # DateTimeOriginal
            found = _parse_exif_text(original) or _parse_exif_text(exif.get(306))  # DateTime
            if found is None:
                found = _parse_png_time(image.info.get("Creation Time"))
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        return None
    return _sane(found, now)


_MAC_EPOCH = 2082844800  # MP4 counts seconds from 1904, Unix from 1970


def _atoms(stream: io.BufferedIOBase | io.BytesIO, start: int, end: int):
    """Yield (type, body_start, body_end) for each atom between start and end."""
    pos = start
    while pos + 8 <= end:
        stream.seek(pos)
        header = stream.read(8)
        if len(header) < 8:
            return
        size, kind = struct.unpack(">I4s", header)
        body = pos + 8
        if size == 1:
            big = stream.read(8)
            if len(big) < 8:
                return
            size = struct.unpack(">Q", big)[0]
            body += 8
        elif size == 0:
            size = end - pos
        if size < 8 or pos + size > end:
            return
        yield kind, body, pos + size
        pos += size


def from_video_data(stream: io.BufferedIOBase | io.BytesIO, size: int) -> int | None:
    """The creation time in an MP4/MOV header (its mvhd atom), if it has one."""
    try:
        for kind, body, stop in _atoms(stream, 0, size):
            if kind != b"moov":
                continue
            for child, cbody, _cstop in _atoms(stream, body, stop):
                if child != b"mvhd":
                    continue
                stream.seek(cbody)
                version = stream.read(4)[0:1]
                raw = stream.read(8 if version == b"\x01" else 4)
                if len(raw) < (8 if version == b"\x01" else 4):
                    return None
                created = struct.unpack(">Q" if version == b"\x01" else ">I", raw)[0]
                return created - _MAC_EPOCH if created > _MAC_EPOCH else None
    except (struct.error, OSError, ValueError):
        return None
    return None


def detect_date(
    data: bytes,
    filename: str,
    kind: str,
    client_modified: int | None = None,
    now: float | None = None,
) -> tuple[int, DateSource]:
    """The best date for a freshly uploaded file, and where it came from."""
    now = time.time() if now is None else now
    if kind == "screenshot":
        found = from_photo_data(data, now)
        if found is not None:
            return found, "photo"
    elif kind == "clip":
        found = _sane(from_video_data(io.BytesIO(data), len(data)), now)
        if found is not None:
            return found, "video"
    found = from_filename(filename, now)
    if found is not None:
        return found, "filename"
    # the browser reports a file's modified time in milliseconds
    if client_modified is not None and client_modified > 10**11:
        client_modified //= 1000
    found = _sane(client_modified, now)
    if found is not None:
        return found, "file"
    return int(now), "uploaded"


def detect_from_stored(path: Path, kind: str) -> tuple[int, DateSource] | None:
    """Re-read a file already saved: photo data first, then its name. Never the
    modified date, because on disk that is only the upload day."""
    now = time.time()
    if kind == "screenshot":
        try:
            found = from_photo_data(path.read_bytes(), now)
        except OSError:
            found = None
        if found is not None:
            return found, "photo"
    elif kind == "clip":
        try:
            with path.open("rb") as handle:
                found = _sane(from_video_data(handle, path.stat().st_size), now)
        except OSError:
            found = None
        if found is not None:
            return found, "video"
    # stored names look like "ab12cd34_<original name>"; drop the id first
    original = path.name.split("_", 1)[1] if "_" in path.name else path.name
    found = from_filename(original, now)
    if found is not None:
        return found, "filename"
    return None
