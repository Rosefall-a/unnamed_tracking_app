from __future__ import annotations

from starlette.requests import Request

from src.api.routes.invitations import InvitationAcceptRequest, InvitationCreateRequest, _public_app_origin


def _request(headers: dict[str, str] | None = None, base_url: str = "http://testserver/") -> Request:
    raw_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    return Request({"type": "http", "headers": raw_headers, "scheme": "http", "server": ("testserver", 80), "path": "/", "query_string": b""})


def test_invitation_email_is_normalized() -> None:
    payload = InvitationCreateRequest(
        username="new-user", email="  New.User@Example.com ", is_admin=False
    )
    assert payload.email == "new.user@example.com"


def test_invitation_rejects_malformed_email() -> None:
    try:
        InvitationCreateRequest(username="new-user", email="not-an-email", is_admin=False)
    except ValueError as exc:
        assert "valid email" in str(exc)
    else:
        raise AssertionError("Malformed invitation email should be rejected")


def test_invitation_password_uses_application_password_policy() -> None:
    payload = InvitationAcceptRequest(token="token", password="Strong-password!1")
    assert payload.password == "Strong-password!1"


def test_invitation_password_rejects_weak_password() -> None:
    try:
        InvitationAcceptRequest(token="token", password="weak")
    except ValueError as exc:
        assert "Password" in str(exc)
    else:
        raise AssertionError("Weak invitation password should be rejected")


def test_public_origin_prefers_browser_origin() -> None:
    request = _request({"origin": "https://archive.example"})
    assert _public_app_origin(request) == "https://archive.example"


def test_public_origin_uses_forwarded_host() -> None:
    request = _request(
        {"x-forwarded-proto": "https", "x-forwarded-host": "archive.example"}
    )
    assert _public_app_origin(request) == "https://archive.example"
