"""Public identity, inert image uploads and real administrator authorization."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image, PngImagePlugin

from src.api.routes.branding import router
from src.core.auth import get_current_user
from src.core.branding import MAX_BRANDING_BYTES, normalize_branding_image
from src.database.session import get_db


def png(size=(24, 16)):
    output = BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("private-comment", "Do not publish image metadata")
    Image.new("RGBA", size, "orange").save(output, format="PNG", pnginfo=metadata)
    return output.getvalue()


@pytest.fixture
def boundary():
    row = SimpleNamespace(
        branding_name=None,
        branding_logo_png=None,
        branding_favicon_png=None,
        tmdb_api_key="private-provider-key",
    )
    db = SimpleNamespace(scalar=AsyncMock(return_value=row), commit=AsyncMock())
    user = SimpleNamespace(is_admin=False)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return app, row, db, user


@pytest.mark.asyncio
async def test_public_reads_do_not_expose_credentials_or_write(boundary):
    app, _, db, _ = boundary
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/branding")
        assert response.json() == {
            "app_name": "Archive",
            "logo_url": None,
            "favicon_url": "/api/branding/default-icon.svg",
        }
        assert (
            (await client.get(response.json()["favicon_url"]))
            .headers["content-type"]
            .startswith("image/svg+xml")
        )
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_members_cannot_change_server_identity(boundary):
    app, row, db, _ = boundary
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.put("/api/branding", json={"app_name": "Other"})).status_code == 403
        assert (
            await client.post("/api/branding/assets/logo", files={"file": ("logo.png", png())})
        ).status_code == 403
        assert (await client.delete("/api/branding/assets/favicon")).status_code == 403
    assert row.branding_name is None
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_name_and_independent_images_preserve_providers(boundary):
    app, row, _, user = boundary
    user.is_admin = True
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put("/api/branding", json={"app_name": "  My library  "})
        assert response.status_code == 200
        assert response.json()["app_name"] == "My library"
        logo = (
            await client.post("/api/branding/assets/logo", files={"file": ("logo.png", png())})
        ).json()
        assert logo["favicon_url"] == logo["logo_url"]
        asset = await client.get(logo["logo_url"])
        assert asset.status_code == 200
        assert asset.headers["content-type"] == "image/png"
        assert "immutable" in asset.headers["cache-control"]
        with Image.open(BytesIO(asset.content)) as image:
            assert not image.info
        icons = (
            await client.post(
                "/api/branding/assets/favicon", files={"file": ("favicon.png", png((32, 32)))}
            )
        ).json()
        assert icons["favicon_url"] != icons["logo_url"]
        removed = (await client.delete("/api/branding/assets/logo")).json()
        assert removed["logo_url"] is None
        assert removed["favicon_url"] == icons["favicon_url"]
        assert (await client.get(logo["logo_url"])).status_code == 404
        assert (await client.delete("/api/branding/assets/favicon")).json()[
            "favicon_url"
        ] == "/api/branding/default-icon.svg"
    assert row.tmdb_api_key == "private-provider-key"


@pytest.mark.parametrize(
    "payload",
    [
        {"app_name": ""},
        {"app_name": " "},
        {"app_name": "x" * 65},
        {"app_name": "bad\x00name"},
        {"app_name": 42},
        {"app_name": "Name", "remote_logo": "https://other"},
    ],
)
@pytest.mark.asyncio
async def test_invalid_name_is_rejected(boundary, payload):
    app, _, db, user = boundary
    user.is_admin = True
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.put("/api/branding", json=payload)).status_code == 422
    db.commit.assert_not_awaited()


@pytest.mark.parametrize(
    "data",
    [b"<svg onload='alert(1)'/>", b"", b"x" * (MAX_BRANDING_BYTES + 1)],
    ids=["svg", "empty", "oversized"],
)
def test_malformed_or_oversized_images_are_rejected(data):
    with pytest.raises(ValueError):
        normalize_branding_image(data)


def test_large_valid_images_are_resized_and_metadata_removed():
    with Image.open(BytesIO(normalize_branding_image(png((1000, 500))))) as image:
        assert image.size == (512, 256)
        assert not image.info


def test_branding_image_orientation_is_applied_and_metadata_removed():
    output = BytesIO()
    image = Image.new("RGB", (40, 20), "orange")
    exif = Image.Exif()
    exif[274] = 6  # Rotate 90 degrees clockwise.
    image.save(output, format="JPEG", exif=exif)
    with Image.open(BytesIO(normalize_branding_image(output.getvalue()))) as normalized:
        assert normalized.size == (20, 40)
        assert not normalized.info


def test_animated_images_are_rejected():
    output = BytesIO()
    frames = [Image.new("RGBA", (16, 16), color) for color in ("red", "blue")]
    frames[0].save(output, format="PNG", save_all=True, append_images=frames[1:])
    with pytest.raises(ValueError, match="static"):
        normalize_branding_image(output.getvalue())
