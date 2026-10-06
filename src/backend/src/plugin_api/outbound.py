"""Bounded JSON HTTP for network-granted plugins running in isolated workers."""

from __future__ import annotations

import json
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 4 * 1024 * 1024


class NoRedirects(HTTPRedirectHandler):
    """Do not forward plugin credentials to a redirect destination."""

    # urllib calls this override with its fixed positional callback signature.
    # pylint: disable-next=too-many-positional-arguments
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirect refused; configure the final server URL.")


def _validated_url(url: object) -> str:
    """Allow HTTP(S) endpoints without URL credentials, fragments or ambiguous separators."""
    if not isinstance(url, str) or len(url) > 8192:
        raise ValueError("Invalid outbound URL.")
    try:
        parts = urlsplit(url)
        _ = parts.port
    except ValueError as exc:
        raise ValueError("Invalid outbound URL.") from exc
    if any(
        (
            parts.scheme not in {"https", "http"},
            not parts.hostname,
            parts.username,
            parts.password,
            parts.fragment,
            any(c.isspace() for c in url),
            "\\" in url,
        )
    ):
        raise ValueError("Use an HTTP(S) URL without credentials or fragment.")
    return url


def _valid_header(key: object, value: object) -> bool:
    if not isinstance(key, str) or not isinstance(value, str):
        return False
    return (
        len(key) <= 128
        and len(value) <= 2048
        and "\n" not in key + value
        and "\r" not in key + value
        and key.lower() in {"accept", "authorization", "x-emby-token"}
    )


def _validated_headers(headers: object) -> dict[str, str]:
    if (
        not isinstance(headers, dict)
        or len(headers) > 16
        or any(not _valid_header(key, value) for key, value in headers.items())
    ):
        raise ValueError("Invalid outbound headers.")
    return headers


def _outbound_request(payload: dict[str, Any]) -> Request:
    """Validate the request before the isolated worker performs any network operation."""
    url = _validated_url(payload.get("url"))
    headers = _validated_headers(payload.get("headers", {}))
    method = payload.get("method", "GET")
    if method not in {"GET", "POST"}:
        raise ValueError("Outbound method must be GET or POST.")
    body_data = None
    if "body" in payload:
        if method != "POST" or not isinstance(payload["body"], dict):
            raise ValueError("Only POST supports an object JSON body.")
        try:
            body_data = json.dumps(payload["body"], allow_nan=False).encode()
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid outbound JSON body.") from exc
        if len(body_data) > 64 * 1024:
            raise ValueError("Outbound request exceeded the 64 KiB limit.")
    return Request(
        url,
        data=body_data,
        method=method,
        headers={
            "Accept": "application/json",
            **headers,
            **({"Content-Type": "application/json"} if body_data else {}),
        },
    )


def outbound_json(payload: dict[str, Any]) -> dict[str, Any]:
    """Bounded JSON GET/POST; never return remote error bodies or credentials."""
    request = _outbound_request(payload)
    try:
        with build_opener(NoRedirects()).open(request, timeout=8) as response:
            body = response.read(MAX_BYTES + 1)
            status = response.status
    except HTTPError as exc:
        code = exc.code
        retry = exc.headers.get("Retry-After", "")
        exc.close()
        result = {"status": code, "error": "Remote server rejected the request."}
        if retry.isdecimal():
            result["retry_after_seconds"] = min(int(retry), 3600)
        return result
    except (URLError, OSError, TimeoutError) as exc:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, ssl.SSLCertVerificationError):
            return {
                "status": 0,
                "code": "certificate_untrusted",
                "error": "The remote TLS certificate is not trusted.",
            }
        return {
            "status": 0,
            "code": "unreachable",
            "error": "Cannot reach the remote server; check TLS and egress.",
        }
    if len(body) > MAX_BYTES:
        raise ValueError("Outbound response exceeded the 4 MiB limit.")
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Remote server returned invalid JSON.") from exc
    if not isinstance(data, (dict, list, bool)):
        raise ValueError("Remote server returned an unexpected JSON shape.")
    return {"status": status, "data": data}
