"""OIDC callback security, account linking, and real browser-session persistence."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from src.api.routes import auth_oidc
from src.core.auth import hash_token, session_cookie_name
from src.core.oidc import OidcConfig
from src.database.models.auth import UserSession
from src.database.models.user import User
from src.database.session import get_db


class CallbackDb:
    """Use a real SQLite session for account and browser-session rows."""

    def __init__(self, session):
        self.session = session

    async def scalar(self, statement):
        return self.session.scalar(statement)

    def add(self, row):
        self.session.add(row)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()


@pytest.fixture
async def callback(monkeypatch):
    engine = create_engine("sqlite://")
    User.__table__.create(engine)
    UserSession.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as session:
        claims = {"sub": "subject", "email": "reader@example.test", "preferred_username": "reader"}
        config = OidcConfig("https://issuer.invalid", "client", "secret", slug="provider")
        client = SimpleNamespace(
            framework=SimpleNamespace(
                get_state_data=AsyncMock(
                    return_value={"nonce": "nonce", "code_verifier": "verifier"}
                ),
                clear_state_data=AsyncMock(),
            ),
            _format_state_params=Mock(side_effect=lambda _state, params: params),
            fetch_access_token=AsyncMock(return_value={"userinfo": claims}),
            parse_id_token=AsyncMock(return_value=claims),
            userinfo=AsyncMock(return_value=claims),
        )
        selected_config = AsyncMock(return_value=config)
        monkeypatch.setattr(auth_oidc, "_get_config", selected_config)
        monkeypatch.setattr(auth_oidc, "register_oidc_provider", Mock())
        monkeypatch.setattr(auth_oidc.oauth, "create_client", Mock(return_value=client))
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="callback-state-test")
        app.include_router(auth_oidc.router)
        app.dependency_overrides[get_db] = lambda: CallbackDb(session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
            yield SimpleNamespace(
                http=http,
                session=session,
                client=client,
                claims=claims,
                config=config,
                selected_config=selected_config,
            )
    engine.dispose()


async def complete(callback, query="?code=code&state=state"):
    return await callback.http.get("/api/auth/oidc/callback" + query)


async def test_oidc_provisions_and_persists_a_cookie_bound_session(callback):
    response = await complete(callback)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?oidc=success"
    user = callback.session.scalar(select(User))
    assert (user.username, user.email, user.oidc_subject) == (
        "reader",
        "reader@example.test",
        "provider:subject",
    )
    assert user.is_active and not user.is_admin
    cookie = response.cookies.get(session_cookie_name("test"))
    stored = callback.session.scalar(select(UserSession))
    assert stored.user_id == user.id
    assert stored.token_hash == hash_token(cookie)
    assert cookie not in stored.token_hash
    assert "httponly" in response.headers["set-cookie"].lower()
    callback.client.framework.clear_state_data.assert_awaited_once()
    callback.client._format_state_params.assert_called_once_with(
        {"nonce": "nonce", "code_verifier": "verifier"}, {"code": "code", "state": "state"}
    )


@pytest.mark.parametrize(
    "case", ["missing_state", "invalid_state", "provider_failure", "missing_identity"]
)
async def test_oidc_rejects_invalid_exchange_without_account_or_session(callback, case):
    query = "?code=code&state=state"
    if case == "missing_state":
        query = "?code=code"
    elif case == "invalid_state":
        callback.client.framework.get_state_data.return_value = None
    elif case == "provider_failure":
        callback.client.fetch_access_token.side_effect = RuntimeError("Unavailable")
    else:
        callback.claims.pop("sub")
    response = await complete(callback, query)
    reason = "identity_missing" if case == "missing_identity" else "authentication_failed"
    assert response.headers["location"] == f"/login?oidc_error={reason}"
    assert callback.session.scalar(select(User.id)) is None
    assert callback.session.scalar(select(UserSession.id)) is None
    assert session_cookie_name("test") not in response.cookies


@pytest.mark.parametrize(
    ("subject", "active", "error"),
    [(None, False, "account_disabled"), ("other:subject", True, "identity_conflict")],
)
async def test_oidc_cannot_link_disabled_or_conflicting_accounts(callback, subject, active, error):
    user = User(
        username="reader",
        email="reader@example.test",
        password_hash="unused",
        oidc_subject=subject,
        is_active=active,
    )
    callback.session.add(user)
    callback.session.commit()
    response = await complete(callback)
    assert response.headers["location"] == f"/login?oidc_error={error}"
    assert user.oidc_subject == subject
    assert callback.session.scalar(select(UserSession.id)) is None


async def test_oidc_user_creation_policy_is_enforced(callback):
    callback.selected_config.return_value = replace(callback.config, allow_new_users=False)
    response = await complete(callback)
    assert response.headers["location"] == "/login?oidc_error=user_creation_disabled"
    assert callback.session.scalar(select(User.id)) is None
    assert callback.session.scalar(select(UserSession.id)) is None


@pytest.mark.parametrize(("groups", "admin"), [(["administrators"], True), (["readers"], False)])
async def test_oidc_links_legacy_subject_and_applies_explicit_admin_group(callback, groups, admin):
    user = User(
        username="reader",
        email="reader@example.test",
        password_hash="unused",
        oidc_subject="subject",
        is_admin=not admin,
    )
    callback.session.add(user)
    callback.session.commit()
    callback.claims["groups"] = groups
    callback.selected_config.return_value = replace(callback.config, admin_group="administrators")
    response = await complete(callback)
    assert response.headers["location"] == "/login?oidc=success"
    assert user.oidc_subject == "provider:subject"
    assert user.is_admin is admin


@pytest.mark.parametrize(
    ("message", "success"), [("Invalid key set format", True), ("Invalid nonce", False)]
)
async def test_oidc_jwks_fallback_preserves_other_identity_validation_errors(
    callback, message, success
):
    callback.client.fetch_access_token.return_value = {"id_token": "id-token"}
    callback.client.parse_id_token.side_effect = ValueError(message)
    response = await complete(callback)
    if success:
        assert response.headers["location"] == "/login?oidc=success"
        callback.client.userinfo.assert_awaited_once()
    else:
        assert response.headers["location"] == "/login?oidc_error=authentication_failed"
        callback.client.userinfo.assert_not_awaited()
        assert callback.session.scalar(select(UserSession.id)) is None
