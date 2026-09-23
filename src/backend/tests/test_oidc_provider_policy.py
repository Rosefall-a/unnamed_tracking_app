from src.core.oidc import OidcConfig


def test_verified_email_requirement_defaults_to_disabled():
    config = OidcConfig(
        issuer_url="https://id.example.com",
        client_id="client",
        client_secret="secret",
    )
    assert config.require_verified_email is False


def test_verified_email_requirement_is_provider_specific():
    strict = OidcConfig(
        issuer_url="https://id.example.com",
        client_id="client",
        client_secret="secret",
        require_verified_email=True,
        slug="strict",
    )
    permissive = OidcConfig(
        issuer_url="https://id.example.com",
        client_id="client",
        client_secret="secret",
        require_verified_email=False,
        slug="permissive",
    )
    assert strict.require_verified_email is True
    assert permissive.require_verified_email is False
