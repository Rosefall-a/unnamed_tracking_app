# OpenID Connect (OIDC) setup

The application supports OIDC/SSO without exposing the identity-provider client secret to the browser. OIDC settings are stored in the deployment database and the client secret is encrypted at rest.

## Prerequisites

- An OIDC provider such as Authentik, Keycloak, Entra ID, Okta, or another standards-compliant provider.
- A client configured for a server-side authorization-code flow.
- The application's public callback URL.

## Provider configuration

Configure the provider with:

- **Redirect URI:** `<APP_ORIGIN>/api/auth/oidc/callback`
- **Grant type:** Authorization Code
- **Scopes:** at least `openid profile email`
- **Response type:** `code`

The issuer field may contain either the provider issuer URL or its full `/.well-known/openid-configuration` discovery URL. The application accepts both forms.

The provider should expose a standards-compliant OpenID discovery document and a usable JWKS endpoint when ID-token validation is used. If a provider's JWKS response is malformed but its authenticated UserInfo endpoint is valid, the callback can fall back to UserInfo after the authorization-code exchange.

## Application configuration

Open **Settings → OIDC / SSO** while signed in as an administrator and configure:

1. Issuer / discovery URL.
2. Client ID.
3. Client secret.
4. Requested scopes.
5. Redirect URI, if it differs from the application's generated callback URL.
6. Optional groups claim and administrator group.
7. Account matching by OIDC email or username.
8. Default login method and SSO button text.

The client secret is sent only to the backend and is encrypted before it is persisted. Do not put an OIDC client secret in frontend environment variables or source control.

Environment variables remain supported as a bootstrap/fallback mechanism for installations that have not configured database-backed OIDC settings.

## Identity and account linking

The callback requires an OIDC `sub` and email. An explicitly false `email_verified` claim is rejected. Existing users are matched according to the configured matching field, then their OIDC subject is linked. A previously linked subject cannot be reassigned to a different account.

New OIDC users receive a generated local password that is not disclosed or usable through the OIDC flow; authentication is performed through the configured identity provider.

If an administrator group is configured, membership in that group controls the application's administrator flag for OIDC-authenticated users.

## Troubleshooting

### `parse_id_token() got an unexpected keyword argument 'leeway'`

This indicates that the application is passing an argument unsupported by the pinned Authlib Starlette client. The application deliberately calls the Authlib 1.4-compatible parser signature and does not pass `leeway`.

### OIDC redirects successfully but `/api/auth/me` returns `401`

Check the backend callback log first. A successful OIDC callback must create a `UserSession` and set the `session` HTTP-only cookie. If the callback returns to `/login?oidc=success` without that cookie, inspect the callback error and the application's cookie security settings. In HTTPS deployments, `AUTH_COOKIE_SECURE` should be enabled.

### User is rejected for missing email

The default account matching mode is email. Ensure the provider includes an `email` claim and does not explicitly set `email_verified` to false. If the provider uses a different identity claim arrangement, configure the provider to expose the standard email claim rather than weakening the verification check.

### Admin group is not applied

Make sure the configured groups claim name matches the claim returned by the provider and that the configured administrator group exactly matches one of its values. The application accepts a single group string or an array of groups.

## Security notes

- Never log authorization codes, access tokens, ID tokens, or client secrets.
- Keep the callback on HTTPS in production.
- Use a confidential OIDC client for the server-side authorization-code exchange.
- Keep the application's session cookie HTTP-only.
- OIDC authentication creates the application's normal server-side session; API requests continue to use that session rather than sending the OIDC token to the frontend.
