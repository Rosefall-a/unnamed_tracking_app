"""Game assets routes, composed by the games router."""

import asyncio
import io
import time
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlparse
from uuid import UUID

import requests
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.game_profiles import _get_profile_or_404
from src.api.routes.utils.games import (
    _DATA_ROOT,
    ALLOWED_ASSET_KINDS,
    _get_game_or_404,
)
from src.core.app_integrations import get_max_upload_size_mb, get_upload_limits_mb
from src.core.auth import get_current_user
from src.database.models.game import Game
from src.database.models.media_item import MediaItem
from src.database.models.user import User
from src.database.session import get_db
from src.features.trash.media_trash import move_media_file_to_trash, restore_media_file_from_trash
from src.features.trash.sweep import RETENTION_SECONDS
from src.helpers.media import MediaKind, classify_media, media_subdir, save_media_bytes
from src.helpers.media_dates import detect_date, detect_from_stored
from src.helpers.range_response import ranged_file_response
from src.helpers.save_game_asset import (
    ASSET_FILENAMES,
    AssetKind,
    save_game_asset,
)

_FILES_DEFAULT = File(None, alias="files")


_FILE_DEFAULT = File(None, alias="file")


_UNSCOPED_ONLY_DEFAULT = Query(False, description="Only items with no profile_id set.")


_DB_DEPENDENCY = Depends(get_db)


_CURRENT_USER_DEPENDENCY = Depends(get_current_user)


_FILE_UPLOAD = File(...)


_NONE_FORM = Form(None)


_MODIFIED_FORM = Form(None)


router = APIRouter()
asset_read_router = APIRouter()


class AssetUrlRequest(BaseModel):
    __module__ = "src.api.routes.games"
    url: str


# Parallel routes/models intentionally share this shape.
# pylint: disable=duplicate-code
@asset_read_router.get("/{game_id}/assets/{asset_kind}", response_class=FileResponse)
async def get_game_asset(
    game_id: UUID,
    asset_kind: AssetKind,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> FileResponse:
    """Return a stored PNG asset for a game."""
    if asset_kind not in ALLOWED_ASSET_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported asset kind '{asset_kind}'. Supported values: {sorted(ALLOWED_ASSET_KINDS)}",
        )

    game = await _get_game_or_404(game_id, db, current_user.id)
    asset_path = (
        _DATA_ROOT
        / str(game.user_id)
        / "games"
        / game.folder_location
        / ASSET_FILENAMES[asset_kind]
    )
    if not asset_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_kind}' has not been uploaded for game {game_id}.",
        )

    return FileResponse(
        asset_path,
        media_type="image/png",
        # was "no-store, max-age=0" — meant the browser re-downloaded every
        # cover/banner on every scroll, reload, and revisit, even when
        # nothing changed. Starlette's FileResponse already sets
        # Last-Modified/ETag from the file's own stat, so a "revalidate"
        # cache still gets a cheap 304 instead of a full re-fetch the
        # instant an asset actually changes (a refresh/re-sync overwrites
        # the file in place, changing its mtime).
        headers={"Cache-Control": "private, max-age=3600, must-revalidate"},
    )


# pylint: enable=duplicate-code


# Parallel routes/models intentionally share this shape.
# pylint: disable=duplicate-code
@router.post(
    "/{game_id}/assets/{asset_kind}",
    responses={
        status.HTTP_200_OK: {"description": "Image uploaded and resized"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid asset kind or upload"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
    },
)
async def upload_game_asset(
    game_id: UUID,
    asset_kind: AssetKind,
    file: UploadFile = _FILE_UPLOAD,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    """Upload and persist artwork for a game."""
    if asset_kind not in ALLOWED_ASSET_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported asset kind '{asset_kind}'. Supported values: {sorted(ALLOWED_ASSET_KINDS)}",
        )

    await _get_game_or_404(game_id, db, current_user.id)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is required.",
        )

    # Do not trust the browser-supplied MIME type here. Some valid image
    # files are reported as application/octet-stream (or with no type at all).
    # save_game_asset decodes the actual image bytes with Pillow, which gives
    # us the real validation without rejecting otherwise valid manual uploads.
    image_bytes = await file.read()
    max_upload_mb = await get_max_upload_size_mb(db)
    max_bytes = max_upload_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image is larger than the {max_upload_mb} MB limit.",
        )

    try:
        target_path = await save_game_asset(image_bytes, game_id, asset_kind)
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not process image: {exc}",
        ) from exc

    return {
        "game_id": str(game_id),
        "asset_kind": asset_kind,
        "path": str(target_path),
        "status": "saved",
    }


# pylint: enable=duplicate-code


@router.post(
    "/{game_id}/assets/{asset_kind}/from-url",
    responses={
        status.HTTP_200_OK: {"description": "Image downloaded and resized"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid URL or image"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
    },
)
async def download_game_asset(
    game_id: UUID,
    asset_kind: AssetKind,
    payload: AssetUrlRequest,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    """Download an image URL and persist it as a normalized game asset."""
    if asset_kind not in ALLOWED_ASSET_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported asset kind '{asset_kind}'.",
        )

    await _get_game_or_404(game_id, db, current_user.id)
    parsed_url = urlparse(payload.url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Image URL must use http or https."
        )

    try:
        response = await asyncio.to_thread(requests.get, payload.url, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not download image: {exc}"
        ) from exc

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="URL did not return an image."
        )
    image_bytes = response.content
    max_upload_mb = await get_max_upload_size_mb(db)
    max_bytes = max_upload_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image is larger than the {max_upload_mb} MB limit.",
        )

    try:
        output_path = await save_game_asset(image_bytes, game_id, asset_kind)
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not save image: {exc}"
        ) from exc

    return {
        "game_id": str(game_id),
        "asset_kind": asset_kind,
        "path": str(output_path),
        "status": "saved",
    }


# Parallel routes/models intentionally share this shape.
# pylint: disable=duplicate-code
def _media_item_to_dict(item: MediaItem, game_id: UUID) -> dict:
    return {
        "id": str(item.id),
        "filename": item.filename,
        "kind": item.kind,
        "url": f"/api/game/{game_id}/screenshots/{item.kind}/{item.filename}",
        "tags": item.tags,
        "note": item.note,
        "linked_achievement_id": str(item.linked_achievement_id)
        if item.linked_achievement_id
        else None,
        "profile_id": str(item.profile_id) if item.profile_id else None,
        "created_at": item.created_at,
        "title": item.title,
        "taken_at": item.taken_at,
        "taken_source": item.taken_source,
        "thumbnail_url": f"/api/game/{game_id}/thumbnails/{item.id}"
        if item.thumb_filename
        else None,
        "duration": item.duration,
    }


# pylint: enable=duplicate-code


_THUMB_MAX_WIDTH = 640
_THUMB_UPLOAD = File(...)
_THUMB_DURATION = Form(None)


def _thumb_dir(game: Game) -> Path:
    return _DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "") / "thumbs"


# Keep the established workflow and public parameters together.
# pylint: disable=too-many-positional-arguments
@router.post("/{game_id}/thumbnails/{media_id}")
async def save_clip_thumbnail(
    game_id: UUID,
    media_id: UUID,
    file: UploadFile = _THUMB_UPLOAD,
    duration: float | None = _THUMB_DURATION,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    """Keep a clip's preview picture, made in the browser when it was uploaded
    (or the first time it was shown), so it never has to be made again. The
    picture is shrunk and saved as a JPEG; the clip's length is kept with it."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    item = await db.scalar(
        select(MediaItem).where(
            MediaItem.id == media_id,
            MediaItem.game_id == game_id,
            MediaItem.kind == "clip",
            MediaItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found.")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Thumbnail is too large."
        )
    try:
        with Image.open(io.BytesIO(data)) as image:
            picture = image.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="That is not a picture."
        ) from exc
    if picture.width > _THUMB_MAX_WIDTH:
        picture = picture.resize(
            (_THUMB_MAX_WIDTH, max(1, round(picture.height * _THUMB_MAX_WIDTH / picture.width)))
        )
    directory = _thumb_dir(game)
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{item.id}.jpg"
    picture.save(directory / name, "JPEG", quality=80)
    item.thumb_filename = name
    if duration is not None and duration > 0:
        item.duration = float(duration)
    await db.commit()
    return _media_item_to_dict(item, game_id)


# pylint: enable=too-many-positional-arguments


@router.get("/{game_id}/thumbnails/{media_id}", response_class=FileResponse)
async def get_clip_thumbnail(
    game_id: UUID,
    media_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> FileResponse:
    game = await _get_game_or_404(game_id, db, current_user.id)
    item = await db.scalar(
        select(MediaItem).where(MediaItem.id == media_id, MediaItem.game_id == game_id)
    )
    path = _thumb_dir(game) / item.thumb_filename if item and item.thumb_filename else None
    if path is None or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No thumbnail yet.")
    # the picture for a given clip never changes, so the browser may keep it
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )


# Keep the established workflow and public parameters together.
# pylint: disable=duplicate-code,too-many-locals,too-many-positional-arguments
@router.post("/{game_id}/screenshots")
async def upload_game_screenshots(
    game_id: UUID,
    files: list[UploadFile] | None = _FILES_DEFAULT,
    file: UploadFile | None = _FILE_DEFAULT,
    profile_id: UUID | None = _NONE_FORM,
    last_modified: list[int] | None = _MODIFIED_FORM,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    """Bulk upload — accepts any mix of images, videos, and audio in one
    request. Images become screenshots, videos become clips, audio becomes
    soundtrack; anything else is rejected per-file (the rest still save).
    Each saved file gets a MediaItem row (not just a file on disk) so it can
    be tagged, noted, and linked to an achievement afterward. An optional
    profile_id tags the whole batch to one account (e.g. an OSRS ironman) —
    useful for a "levelup dump from this account" upload in one go."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    if not game.folder_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Game folder_location is missing."
        )
    if profile_id is not None:
        await _get_profile_or_404(profile_id, game_id, db)

    # Accept both the current plural field used by the frontend and the
    # legacy/single-file field used by older clients. This keeps the upload
    # endpoint backwards-compatible while still returning a useful 400 when
    # a multipart request contains no file at all.
    uploads = list(files or [])
    if file is not None:
        uploads.append(file)
    if not uploads:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required.",
        )

    results: list[dict] = []
    for index, upload in enumerate(uploads):
        kind = classify_media(upload.content_type, upload.filename or "")
        if kind is None:
            results.append(
                {
                    "filename": upload.filename,
                    "status": "rejected",
                    "reason": "Unsupported file type.",
                }
            )
            continue

        # clips/soundtrack get a much larger cap than images — a real video
        # clip routinely exceeds a cover-art-sized limit
        limit_mb = (
            (await get_upload_limits_mb(db))["max_clip_size_mb"]
            if kind in ("clip", "soundtrack")
            else await get_max_upload_size_mb(db)
        )
        max_bytes = limit_mb * 1024 * 1024

        data = await upload.read()
        if len(data) > max_bytes:
            results.append(
                {
                    "filename": upload.filename,
                    "status": "rejected",
                    "reason": f"Larger than {limit_mb} MB.",
                }
            )
            continue

        dest_dir = (
            _DATA_ROOT / str(game.user_id) / "games" / game.folder_location / media_subdir(kind)
        )
        saved_path = save_media_bytes(data, dest_dir, upload.filename or "file")
        taken_at, taken_source = detect_date(
            data,
            upload.filename or "",
            kind,
            last_modified[index] if last_modified and index < len(last_modified) else None,
        )
        db.add(
            MediaItem(
                game_id=game_id,
                kind=kind,
                filename=saved_path.name,
                profile_id=profile_id,
                taken_at=taken_at,
                taken_source=taken_source,
            )
        )
        results.append({"filename": saved_path.name, "status": "saved", "kind": kind})

    await db.commit()
    return {"results": results}


# pylint: enable=duplicate-code,too-many-locals,too-many-positional-arguments


# Parallel routes/models intentionally share this shape.
# pylint: disable=duplicate-code
@router.get("/{game_id}/screenshots")
async def list_game_screenshots(
    game_id: UUID,
    profile_id: UUID | None = _NONE_FORM,
    unscoped_only: bool = _UNSCOPED_ONLY_DEFAULT,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    await _get_game_or_404(game_id, db, current_user.id)
    stmt = select(MediaItem).where(MediaItem.game_id == game_id, MediaItem.deleted_at.is_(None))
    if profile_id is not None:
        stmt = stmt.where(MediaItem.profile_id == profile_id)
    elif unscoped_only:
        stmt = stmt.where(MediaItem.profile_id.is_(None))
    result = await db.execute(stmt.order_by(MediaItem.created_at.desc()))
    return {"media": [_media_item_to_dict(item, game_id) for item in result.scalars().all()]}


# pylint: enable=duplicate-code


# Keep the established workflow and public parameters together.
# pylint: disable=duplicate-code,too-many-positional-arguments
@router.get("/{game_id}/screenshots/{kind}/{filename}", response_class=FileResponse)
async def get_game_screenshot(
    request: Request,
    game_id: UUID,
    kind: MediaKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> Response:
    game = await _get_game_or_404(game_id, db, current_user.id)
    path = (
        _DATA_ROOT
        / str(game.user_id)
        / "games"
        / (game.folder_location or "")
        / media_subdir(kind)
        / Path(filename).name
    )
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found.")
    return ranged_file_response(request, path)


# pylint: enable=duplicate-code,too-many-positional-arguments


class DetectDatesRequest(BaseModel):
    __module__ = "src.api.routes.games"
    ids: list[UUID]


class MediaItemUpdate(BaseModel):
    __module__ = "src.api.routes.games"
    tags: list[str] | None = None
    note: str | None = None
    linked_achievement_id: UUID | None = None
    profile_id: UUID | None = None
    title: str | None = Field(default=None, max_length=200)
    taken_at: int | None = None
    # "achievement" when the date was copied from an achievement's unlock time
    taken_source: Literal["manual", "achievement"] | None = None


@router.post("/{game_id}/screenshots/detect-dates")
async def detect_media_dates(
    game_id: UUID,
    payload: DetectDatesRequest,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    """Re-read the date from the files themselves (photo data, then the file
    name) for the chosen items. Files with nothing to read keep their date, so
    a date you set by hand is only replaced when the file really has one."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    items = (
        await db.scalars(
            select(MediaItem).where(
                MediaItem.game_id == game_id,
                MediaItem.id.in_(payload.ids),
                MediaItem.deleted_at.is_(None),
            )
        )
    ).all()
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    changed: list[dict] = []
    for item in items:
        found = detect_from_stored(
            game_dir / media_subdir(cast(MediaKind, item.kind)) / item.filename, item.kind
        )
        if found is None:
            continue
        item.taken_at, item.taken_source = found
        changed.append(_media_item_to_dict(item, game_id))
    await db.commit()
    return {"media": changed}


# Parallel routes/models intentionally share this shape.
# pylint: disable=duplicate-code
@router.patch("/{game_id}/screenshots/{media_id}")
async def update_media_item(
    game_id: UUID,
    media_id: UUID,
    payload: MediaItemUpdate,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    await _get_game_or_404(game_id, db, current_user.id)
    item = await db.scalar(
        select(MediaItem).where(MediaItem.id == media_id, MediaItem.game_id == game_id)
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "title" in changes and changes["title"] is not None:
        changes["title"] = changes["title"].strip() or None
    source = changes.pop("taken_source", None)
    for field, value in changes.items():
        setattr(item, field, value)
    if "taken_at" in changes:
        # a date typed in by hand, or cleared back to the upload date
        item.taken_source = (source or "manual") if changes["taken_at"] is not None else None
    await db.commit()
    await db.refresh(item)
    return _media_item_to_dict(item, game_id)


# pylint: enable=duplicate-code


@router.delete("/{game_id}/screenshots/{kind}/{filename}")
async def delete_game_screenshot(
    game_id: UUID,
    kind: MediaKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    """Soft-delete: moves the file to trash and marks its row deleted
    rather than removing it — restorable for 7 days, same as game
    archives (features/trash/sweep.py does the eventual real deletion)."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    item = await db.scalar(
        select(MediaItem).where(
            MediaItem.game_id == game_id,
            MediaItem.kind == kind,
            MediaItem.filename == filename,
            MediaItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    path = game_dir / media_subdir(kind) / Path(filename).name
    move_media_file_to_trash(path, game_dir, kind)
    item.deleted_at = int(time.time())
    await db.commit()
    return {"status": "trashed", "filename": filename}


@router.get("/{game_id}/screenshots/trash")
async def list_game_screenshot_trash(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    await _get_game_or_404(game_id, db, current_user.id)
    result = await db.execute(
        select(MediaItem)
        .where(MediaItem.game_id == game_id, MediaItem.deleted_at.is_not(None))
        .order_by(MediaItem.deleted_at.desc())
    )
    media = []
    for item in result.scalars().all():
        assert item.deleted_at is not None  # guaranteed by the deleted_at.is_not(None) filter above
        media.append(
            {
                **_media_item_to_dict(item, game_id),
                "deleted_at": item.deleted_at,
                "purge_at": item.deleted_at + RETENTION_SECONDS,
            }
        )
    return {"media": media}


@router.post("/{game_id}/screenshots/{kind}/{filename}/restore")
async def restore_game_screenshot(
    game_id: UUID,
    kind: MediaKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    game = await _get_game_or_404(game_id, db, current_user.id)
    item = await db.scalar(
        select(MediaItem).where(
            MediaItem.game_id == game_id,
            MediaItem.kind == kind,
            MediaItem.filename == filename,
            MediaItem.deleted_at.is_not(None),
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deleted media item not found."
        )
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    restore_media_file_from_trash(filename, game_dir / media_subdir(kind), game_dir, kind)
    item.deleted_at = None
    await db.commit()
    return _media_item_to_dict(item, game_id)
