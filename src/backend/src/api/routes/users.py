from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(
    prefix="/api/user",
    tags=["user"],
    dependencies=[Depends(get_current_user)],
)

_USER_DATA_ROOT = Path("/data/user")
_PROFILE_FILENAME = "profile.png"
_MAX_PROFILE_SIZE = 10 * 1024 * 1024


async def _get_user_or_404(user_id: UUID, db: AsyncSession) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return user


async def _get_authorized_user(
    user_id: UUID,
    db: AsyncSession,
    current_user: User,
) -> User:
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this user's profile.",
        )
    return await _get_user_or_404(user_id, db)


def _profile_path(user_id: UUID) -> Path:
    return _USER_DATA_ROOT / str(user_id) / _PROFILE_FILENAME


def profile_picture_version(user_id: UUID) -> int | None:
    """When the user's picture was last saved (unix milliseconds), or None
    when they have none. The app puts it in the picture's address, so it asks
    for a picture only when there is one, and a browser can keep the picture
    until a new one is uploaded (which changes the address)."""
    try:
        return _profile_path(user_id).stat().st_mtime_ns // 1_000_000
    except OSError:
        return None


def _is_heic(data: bytes) -> bool:
    # HEIC/HEIF files are an ISO box whose "ftyp" brand names the format;
    # Pillow cannot read them, so say so instead of "not a valid image"
    return data[4:8] == b"ftyp" and data[8:12] in {
        b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1",
    }


@router.put("/{user_id}/profile-picture")
async def upload_profile_picture(
    user_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Validate and save a user's profile picture as profile.png."""
    await _get_authorized_user(user_id, db, current_user)

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile picture is empty.",
        )
    if len(image_bytes) > _MAX_PROFILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Profile picture must be 10 MB or smaller.",
        )

    if _is_heic(image_bytes):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="HEIC pictures are not supported. Save it as a JPEG or PNG and try again.",
        )

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.load()
            profile_image = image.convert("RGBA")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a valid image.",
        ) from exc

    profile_directory = _USER_DATA_ROOT / str(user_id)
    profile_directory.mkdir(parents=True, exist_ok=True)
    target_path = profile_directory / _PROFILE_FILENAME
    temporary_path = profile_directory / f".{_PROFILE_FILENAME}.tmp"

    try:
        profile_image.save(temporary_path, format="PNG")
        temporary_path.replace(target_path)
    except OSError as exc:
        if temporary_path.exists():
            temporary_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save profile picture.",
        ) from exc
    finally:
        profile_image.close()

    return {
        "user_id": str(user_id),
        "path": str(target_path),
        "status": "saved",
        "version": str(profile_picture_version(user_id)),
    }


@router.get("/{user_id}/profile-picture", response_class=FileResponse)
async def get_profile_picture(
    user_id: UUID,
    v: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Return the user's stored profile picture. Asked for with its version
    (`?v=`, see profile_picture_version) the answer never changes, so the
    browser may keep it; without one it must not be kept."""
    await _get_authorized_user(user_id, db, current_user)
    target_path = _profile_path(user_id)
    if not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile picture not found for user {user_id}.",
        )

    cache = "private, max-age=31536000, immutable" if v else "no-store, max-age=0"
    return FileResponse(target_path, media_type="image/png", headers={"Cache-Control": cache})
