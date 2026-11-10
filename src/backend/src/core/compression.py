"""Gzip for the responses it helps, and not for the ones it does not.

Lists and pages of JSON shrink about tenfold, so they are compressed. Covers,
screenshots, clips, backups and other files are already compressed (or, for a
backup's files copy, made of compressed pictures): gzipping them on every
request only costs CPU, and it drops the size the browser needs to show how
far a download has got. Starlette's own middleware in the version used here
compresses everything, so those types are passed through untouched.
"""

from __future__ import annotations

from starlette.datastructures import Headers
from starlette.middleware.gzip import GZipMiddleware, GZipResponder
from starlette.types import Message, Receive, Scope, Send

_ALREADY_COMPRESSED_PREFIXES = ("image/", "video/", "audio/", "font/")
_ALREADY_COMPRESSED_TYPES = frozenset(
    {
        "application/octet-stream",
        "application/x-tar",
        "application/zip",
        "application/gzip",
        "application/pdf",
    }
)


def already_compressed(content_type: str) -> bool:
    kind = content_type.split(";", 1)[0].strip().lower()
    if kind == "image/svg+xml":
        return False
    return kind in _ALREADY_COMPRESSED_TYPES or kind.startswith(_ALREADY_COMPRESSED_PREFIXES)


class _Responder(GZipResponder):
    async def send_with_gzip(self, message: Message) -> None:
        await super().send_with_gzip(message)
        if message["type"] == "http.response.start" and already_compressed(
            Headers(raw=message["headers"]).get("content-type", "")
        ):
            # the same path Starlette takes for a response that is already encoded
            self.content_encoding_set = True


class SelectiveGZipMiddleware(GZipMiddleware):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and "gzip" in Headers(scope=scope).get("Accept-Encoding", ""):
            responder = _Responder(self.app, self.minimum_size, compresslevel=self.compresslevel)
            await responder(scope, receive, send)
            return
        await self.app(scope, receive, send)
