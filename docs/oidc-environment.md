# OIDC environment overrides

OIDC providers can be managed by the setup environment tree. The provider name is
the second component of the variable:

    OIDC__AUTHENTIK__NAME=Authentik
    OIDC__AUTHENTIK__ISSUER_URL=https://auth.example.com
    OIDC__AUTHENTIK__CLIENT_ID=archive
    OIDC__AUTHENTIK__CLIENT_SECRET=secret
    OIDC__AUTHENTIK__SHOW_ON_LOGIN=true
    OIDC__AUTHENTIK__AUTOSTART_ENABLED=true
    OIDC__AUTHENTIK__REQUIRE_VERIFIED_EMAIL=false

Environment values are authoritative. They are intended for deployments where
SSO configuration is centrally managed and should not be changed through the UI.

Verified email is optional per provider and defaults to false. The provider still
requires an email claim for account matching; disabling the policy only removes
the requirement that the identity provider mark that claim as verified.

Provider order, login visibility, autostart URLs, button styling, user matching,
and account-creation policy are independent per-provider settings.
