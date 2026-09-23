# OIDC setup integration

OIDC setup is built on the declarative SetupConfiguration tree.

A provider is addressed by:

    OIDC__<provider-name>__<field>

Nested fields are supported for future policy groups.

## Adding an OIDC provider setting

1. Add the field to the provider data model/interface.
2. Add its default to the provider creation helper.
3. Load the field from stored provider JSON.
4. Apply environment overrides before validation/save.
5. Add the field to the setup form if it is user-configurable.
6. Document the variable under /docs.
7. Add a regression test for both the default and an environment override.

## Verified-email policy

The require_verified_email field is deliberately stored per provider. The
authentication callback must test this value before rejecting an unverified
email claim.

The default is false for backwards-compatible deployments that do not require
the identity provider to assert email verification.

## Multiple providers

Do not collapse named providers into one global OIDC configuration. Each provider
has its own slug, credentials, display settings, enabled state, login visibility,
and autostart policy. This allows /login/<slug> to select one provider without
changing the normal login page.
