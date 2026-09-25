# OpenID Connect / SSO

Unnamed Tracking App supports OpenID Connect (OIDC) as a server-side SSO login method. The identity-provider client secret stays on the backend, and a successful OIDC login creates the application's normal server-side session.

## Configure OIDC

OIDC can be configured during first-run setup or later under **Settings → OIDC / SSO**.

The generated setup configuration requires:

- **Provider name** and **provider slug** for named-provider configuration.
- **Issuer / discovery URL**.
- **Client ID**.
- **Client secret**.
- **Scopes**, defaulting to `openid profile email`.
- **Groups claim**, defaulting to `groups`.
- Optional **administrator group**.
- **User matching** by email or username, defaulting to email.
- Whether new users may be created.
- Default login method and login-button text.

The issuer may be the provider issuer URL or a full `/.well-known/openid-configuration` URL.

When the OIDC section is selected during setup, issuer URL, client ID, and client secret are required. A complete provider is enabled when setup saves it.

### Environment configuration

The backend configuration registry supports OIDC values from the environment. Environment values take precedence over persisted configuration and are locked in the generated setup UI.

The supported OIDC variables are listed on the [Environment Variables](../setup/environment-variables.md) page.

## Redirect URI

The normal setup flow generates the redirect URI from the address currently used to access the application.

For the default provider:

```text
<APP_ORIGIN>/api/auth/oidc/callback
```

For a named provider:

```text
<APP_ORIGIN>/api/auth/oidc/callback/<provider-slug>
```

Setup displays the generated URI as a read-only value. Runtime authentication also derives the callback from the current request when no deployment-provided redirect URI is supplied.

The backend does support `OIDC_REDIRECT_URI` as a configuration value. If it is supplied through the environment, the runtime can use that configured URI; otherwise the current request is used. For normal deployments, prefer the generated URI so the identity provider follows the actual public application address.

Configure the identity provider for the authorization-code flow using the callback URI shown by the application.

## Account matching and creation

After the authorization-code exchange, the application requires both:

- an OIDC `sub` (subject); and
- an email identity claim.

A verified email is **not** required. An `email_verified: false` claim is not rejected merely because it is false.

Existing accounts are matched according to **Match users by**:

- `email` — match the local account's email address;
- `username` — match the OIDC `preferred_username` or `name`.

Once matched, the OIDC subject is linked to the account. A subject already linked to a different account is rejected as an identity conflict.

If **Allow new users** is enabled, an unmatched OIDC identity creates a local account with a generated password that is not exposed to the user. If it is disabled, unmatched users receive a user-creation-disabled error instead.

## Administrator groups

If an administrator group is configured, the application reads the configured groups claim. Membership in that group controls the user's `is_admin` flag when the OIDC account is created or updated.

The groups claim can be either a string or a list-like claim value.

## Named providers

**Settings → OIDC / SSO** supports multiple named providers. Each provider can have its own:

- name and slug;
- issuer and client credentials;
- scopes and groups claim;
- administrator group;
- user matching rule;
- new-user policy;
- login button text/image;
- enabled state;
- show-on-login state;
- autostart state.

Providers can be reordered. A direct `/api/auth/oidc/login/<provider-slug>` request only starts a named provider when its autostart setting allows it.

## Security

- Keep OIDC callbacks on HTTPS in production.
- Do not expose client secrets to frontend code.
- Do not log authorization codes, access tokens, ID tokens, or client secrets.
- OIDC uses the application's HTTP-only server-side session cookie after login.
- If HTTPS is terminated by a reverse proxy, configure `AUTH_COOKIE_SECURE=true`.
