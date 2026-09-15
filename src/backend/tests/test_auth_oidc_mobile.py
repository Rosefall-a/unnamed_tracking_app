from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response

from src.api.routes.auth_oidc import (
    MobileExchangeRequest,
    _pkce_challenge,
    _valid_challenge,
    mobile_oidc_exchange,
)
from src.core.auth import SESSION_COOKIE
from src.database.models.auth import UserSession


def test_pkce_challenge_is_url_safe_sha256() -> None:
    verifier = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~"

    challenge = _pkce_challenge(verifier)

    assert challenge == "ImpiCd8pp4MveCNnbIS7-GXEtB0xF5HMIDoWqvGA5ig"
    assert _valid_challenge(challenge)
    assert not _valid_challenge("short")


@pytest.mark.asyncio
async def test_mobile_exchange_consumes_handoff_and_sets_session_cookie(monkeypatch) -> None:
    verifier = "a" * 64
    handoff = SimpleNamespace(user_id=uuid4(), verifier_challenge=_pkce_challenge(verifier))
    db = AsyncMock()
    db.scalar.return_value = handoff
    db.add = Mock()
    response = Response()
    monkeypatch.setattr("src.api.routes.auth_oidc.time.time", lambda: 1_000)
    monkeypatch.setattr("src.api.routes.auth_oidc.secrets.token_urlsafe", lambda _: "session-secret")

    result = await mobile_oidc_exchange(
        MobileExchangeRequest(code="handoff-code-that-is-long-enough-1234", verifier=verifier),
        response,
        db,
    )

    assert result == {"status": "logged_in"}
    session = db.add.call_args.args[0]
    assert isinstance(session, UserSession)
    assert session.user_id == handoff.user_id
    assert session.expires_at > 1_000
    db.delete.assert_awaited_once_with(handoff)
    db.commit.assert_awaited_once()
    assert f"{SESSION_COOKIE}=" in response.headers["set-cookie"]
    assert "session-secret" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_mobile_exchange_rejects_wrong_verifier_without_consuming_handoff() -> None:
    handoff = SimpleNamespace(user_id=uuid4(), verifier_challenge=_pkce_challenge("a" * 64))
    db = AsyncMock()
    db.scalar.return_value = handoff
    db.add = Mock()

    with pytest.raises(HTTPException) as failure:
        await mobile_oidc_exchange(
            MobileExchangeRequest(
                code="handoff-code-that-is-long-enough-1234",
                verifier="b" * 64,
            ),
            Response(),
            db,
        )

    assert failure.value.status_code == 401
    db.add.assert_not_called()
    db.delete.assert_not_awaited()
    db.commit.assert_not_awaited()
