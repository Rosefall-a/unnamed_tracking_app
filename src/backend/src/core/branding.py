"""Public deployment identity and bounded, inert branding image conversion."""

from hashlib import sha256
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.app_integration_settings import AppIntegrationSettings

DEFAULT_APP_NAME = "Archive"
MAX_BRANDING_BYTES = 2 * 1024 * 1024
DEFAULT_ICON = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="18" fill="#f7ead8"/>
<g fill="none" stroke="#a4520d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
<path d="M15 23l17-8 17 8-17 8-17-8zM15 32l17 8 17-8M15 41l17 8 17-8"/>
</g></svg>"""


def branding_asset_url(kind: str, data: bytes | None) -> str | None:
    """Content addresses avoid stale icons after an administrator changes branding."""
    return f"/api/branding/assets/{kind}/{sha256(data).hexdigest()}.png" if data else None


def public_branding(row: AppIntegrationSettings | None) -> dict[str, str | None]:
    """Never serialize unrelated deployment configuration or provider credentials."""
    logo = row.branding_logo_png if row else None
    favicon = row.branding_favicon_png if row else None
    return {
        "app_name": (row.branding_name if row else None) or DEFAULT_APP_NAME,
        "logo_url": branding_asset_url("logo", logo),
        "favicon_url": branding_asset_url("favicon", favicon)
        or branding_asset_url("logo", logo)
        or "/api/branding/default-icon.svg",
    }


async def load_branding(db: AsyncSession) -> AppIntegrationSettings | None:
    """Anonymous reads have no write side effects; startup owns singleton creation."""
    return await db.scalar(select(AppIntegrationSettings).limit(1))


def normalize_branding_image(data: bytes) -> bytes:
    """Decode a static image, bound its size, strip metadata and emit PNG only."""
    if not data or len(data) > MAX_BRANDING_BYTES:
        raise ValueError("Choose a PNG, JPEG or WebP image no larger than 2 MB.")
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"} or getattr(image, "n_frames", 1) != 1:
                raise ValueError("Choose a static PNG, JPEG or WebP image.")
            if image.width > 4096 or image.height > 4096 or image.width * image.height > 16_000_000:
                raise ValueError(
                    "Branding images must be at most 4096 pixels per side and 16 megapixels."
                )
            ImageOps.exif_transpose(image, in_place=True)
            normalized = image.convert("RGBA")
            normalized.thumbnail((512, 512), Image.Resampling.LANCZOS)
            # A new image carries no EXIF, comments, embedded profiles or executable content.
            clean = Image.new("RGBA", normalized.size)
            clean.paste(normalized)
            output = BytesIO()
            clean.save(output, format="PNG", optimize=True)
            return output.getvalue()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("The branding image could not be decoded.") from exc


def pwa_branding_icon(data: bytes, size: int, background: str) -> bytes:
    """Place the normalized logo inside the maskable icon's central safe area."""
    with Image.open(BytesIO(data)) as image:
        logo = image.convert("RGBA")
        logo.thumbnail((int(size * 0.7), int(size * 0.7)), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), background)
        canvas.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
        output = BytesIO()
        canvas.save(output, format="PNG")
        return output.getvalue()
