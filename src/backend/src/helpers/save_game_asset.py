from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Literal
from uuid import UUID

from PIL import Image
from sqlalchemy import select

from src.database.models.game import Game
from src.database.session import SessionLocal

DATA_ROOT = Path("/data/games")

AssetKind = Literal["key_art", "banner", "logo", "icon"]

ASSET_SIZES: dict[AssetKind, tuple[int, int]] = {
    "key_art": (600, 900),
    "banner": (3840, 1240),
    "logo": (1024, 1024),
    "icon": (512, 512),
}

ASSET_FILENAMES: dict[AssetKind, str] = {
    "key_art": "key_art.png",
    "banner": "banner.png",
    "logo": "logo.png",
    "icon": "icon.png",
}


def _load_image_bytes(image: bytes | str | Path | Image.Image) -> Image.Image:
    if isinstance(image, Image.Image):
        return image.convert("RGBA")

    if isinstance(image, (str, Path)):
        with Image.open(image) as img:
            return img.convert("RGBA")

    with Image.open(BytesIO(image)) as img:
        return img.convert("RGBA")


def _resize_to_fit(image: Image.Image, width: int, height: int) -> Image.Image:
    original = image.convert("RGBA")
    resized = original.resize((width, height), Image.Resampling.LANCZOS)
    return resized


async def get_game_folder(game_id: UUID | str) -> str:
    async with SessionLocal() as session:
        game = await session.scalar(select(Game).where(Game.id == str(game_id)))
        if game is None:
            raise ValueError(f"Game not found for id: {game_id}")
        if not game.folder_location:
            raise ValueError(f"Game {game_id} is missing folder_location")
        return game.folder_location


async def save_game_asset(
    image: bytes | str | Path | Image.Image,
    game_id: UUID | str,
    asset_kind: AssetKind,
) -> Path:
    """Resize one image to the exact target size for a game asset and save it to disk.

    Example:
        await save_game_asset(image_bytes, game_id, "key_art")
    """
    if asset_kind not in ASSET_SIZES:
        raise ValueError(f"Unsupported asset kind: {asset_kind}")

    folder_name = await get_game_folder(game_id)
    output_dir = DATA_ROOT / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)

    width, height = ASSET_SIZES[asset_kind]
    image_obj = _load_image_bytes(image)
    resized = _resize_to_fit(image_obj, width, height)

    output_path = output_dir / ASSET_FILENAMES[asset_kind]
    resized.save(output_path, format="PNG")
    return output_path


async def save_game_key_art(image: bytes | str | Path | Image.Image, game_id: UUID | str) -> Path:
    return await save_game_asset(image, game_id, "key_art")


async def save_game_banner(image: bytes | str | Path | Image.Image, game_id: UUID | str) -> Path:
    return await save_game_asset(image, game_id, "banner")


async def save_game_logo(image: bytes | str | Path | Image.Image, game_id: UUID | str) -> Path:
    return await save_game_asset(image, game_id, "logo")


async def save_game_icon(image: bytes | str | Path | Image.Image, game_id: UUID | str) -> Path:
    return await save_game_asset(image, game_id, "icon")
