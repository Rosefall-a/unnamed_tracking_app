# OpenID Connect (OIDC) setup

The application supports OIDC/SSO without exposing identity-provider client secrets to the browser. OIDC settings are stored in the deployment database and secrets are encrypted at rest.

## Configuration

OIDC can be configured during first-run setup or later under Settings → OIDC / SSO.

The central setup registry provides:

- Enable OIDC — enabled by default.
- Issuer / discovery URL.
- Client ID.
- Client secret.
- Scopes.
- Groups claim.
- Administrator group.
- User matching by email or username.
- Default login method.

When Enable OIDC is off, incomplete provider credentials are allowed to be saved. This lets an administrator enter a provider before all credentials are available. OIDC login remains disabled until it is enabled and a usable provider exists.

Environment variables are authoritative. If an OIDC value is present in .env, the corresponding setup/settings control is locked.

## Provider configuration

Configure the identity provider for the browser-facing callback:

- Redirect URI: <APP_ORIGIN>/api/auth/oidc/callback
- Grant type: Authorization Code
- Scopes: normally openid profile email
- Response type: code

The issuer field may contain the provider issuer URL or its full /.well-known/openid-configuration discovery URL.

## Identity and account linking

The callback requires a subject (sub) and an email identity claim. A verified email is not required for OIDC login. An explicitly false email_verified claim is not used as a login requirement.

Existing users are matched according to the configured matching field and then their OIDC subject is linked. A previously linked subject cannot be reassigned to another account.

New OIDC users receive a generated local password that is not disclosed or usable through the OIDC flow. Authentication is performed through the configured identity provider.

If an administrator group is configured, membership in that group controls the application administrator flag for OIDC-authenticated users.

## Named providers

Settings → OIDC / SSO supports multiple named providers. Each provider can have:

- a unique name and slug;
- its own issuer/client credentials;
- scopes and claim settings;
- login button text, image, and colour;
- enabled/disabled state;
- show-on-login state;
- autostart state;
- an automatically generated callback URL.

Providers can be reordered. Direct /login/<slug> URLs only start providers whose autostart setting is enabled.

## Security notes

- Never log authorization codes, access tokens, ID tokens, or client secrets.
- Keep the callback on HTTPS in production.
- Use a confidential OIDC client for the server-side authorization-code exchange.
- Keep the application's session cookie HTTP-only.
- OIDC authentication creates the application's normal server-side session.
