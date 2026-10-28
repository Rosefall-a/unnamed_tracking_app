"""A single sign-on provider that says it has not verified an email must not be
used to reach an account that has that email."""

import pytest

from src.api.routes.auth_oidc import email_is_unverified


@pytest.mark.parametrize("claims", [{"email_verified": False}, {"email_verified": "false"}, {"email_verified": "False "}])
def test_an_email_the_provider_says_is_unverified_is_refused(claims) -> None:
    assert email_is_unverified(claims)


@pytest.mark.parametrize("claims", [{"email_verified": True}, {"email_verified": "true"}, {}, {"email_verified": None}])
def test_a_verified_or_unreported_email_is_not_refused(claims) -> None:
    assert not email_is_unverified(claims)
