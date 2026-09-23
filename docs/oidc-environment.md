# OIDC environment overrides

OIDC providers use the setup environment tree. The provider name is the second component.

Example:

OIDC__AUTHENTIK__NAME=Authentik
OIDC__AUTHENTIK__ISSUER_URL=https://auth.example.com
OIDC__AUTHENTIK__CLIENT_ID=archive
OIDC__AUTHENTIK__CLIENT_SECRET=secret
OIDC__AUTHENTIK__SHOW_ON_LOGIN=true
OIDC__AUTHENTIK__AUTOSTART_ENABLED=true
OIDC__AUTHENTIK__REQUIRE_VERIFIED_EMAIL=false

Environment-controlled provider fields are authoritative over setup-form values.

Verified email is optional per provider and defaults to false. The identity must still provide an email claim for matching; disabling the policy only removes the requirement that the provider mark that email as verified.

Each named provider independently controls enabled state, login visibility, ordering, autostart, button presentation, user matching, new-user policy, and verified-email policy.

Client secrets remain backend-only and are stored encrypted. The settings API reports whether a secret is configured without returning the secret.

## Testing

Test two providers, ordering, enabled/disabled, login visibility, autostart, email and username matching, new-user policy, verified-email false/true, and environment-managed values.
