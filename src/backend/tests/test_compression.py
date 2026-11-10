"""JSON is gzipped; pictures, clips and backup files are sent as they are,
with their size, so a download shows how far it has got."""

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from src.core.compression import SelectiveGZipMiddleware, already_compressed

_BODY = b"x" * 5000


def _app() -> Starlette:
    def picture(_request):
        return Response(_BODY, media_type="image/webp")

    def backup(_request):
        return Response(_BODY, media_type="application/x-tar")

    def listing(_request):
        return JSONResponse({"items": ["title"] * 500})

    app = Starlette(
        routes=[Route("/picture", picture), Route("/backup", backup), Route("/list", listing)]
    )
    app.add_middleware(SelectiveGZipMiddleware, minimum_size=1024)
    return app


@pytest.mark.parametrize("path", ["/picture", "/backup"])
async def test_files_are_sent_as_they_are(path) -> None:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path, headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in response.headers
    assert response.headers["content-length"] == str(len(_BODY))
    assert response.content == _BODY


async def test_json_is_still_compressed() -> None:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/list", headers={"Accept-Encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"
    assert response.json() == {"items": ["title"] * 500}


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("image/jpeg", True),
        ("video/mp4", True),
        ("application/octet-stream", True),
        ("image/svg+xml", False),
        ("application/json", False),
        ("text/html; charset=utf-8", False),
    ],
)
def test_which_types_count_as_already_compressed(content_type, expected) -> None:
    assert already_compressed(content_type) is expected
