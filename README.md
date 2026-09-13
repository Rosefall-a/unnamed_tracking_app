# Authentication setup

New installations no longer require an administrator username, email, or password in `.env`. After the database migrations complete, open the application and it will redirect to `/setup`, where the first administrator creates their account. The setup endpoint is one-time and creates the first administrator plus a normal 30-day HttpOnly session.

## OIDC / SSO

OIDC is optional. Set these variables in the backend environment:

- `OIDC_ISSUER_URL` — the provider issuer, for example the realm/tenant issuer URL.
- `OIDC_CLIENT_ID` — the client/application ID.
- `OIDC_CLIENT_SECRET` — the client secret.
- `OIDC_REDIRECT_URI` — the registered callback URL; if omitted, it is derived from the incoming request.
- `OIDC_SCOPES` — defaults to `openid profile email`.

Register the callback as `/api/auth/oidc/callback` on the public application URL. When configured, the login page shows **Continue with SSO**. The backend uses the provider's discovery metadata and authorization-code flow, requires a `sub` and verified email, links an existing account by OIDC subject or verified email, and otherwise creates a normal non-admin account. OIDC accounts receive the same server-side session cookie as password logins; provider access/ID tokens are not stored in the database.

Existing deployments may continue to use `PRIMARY_USER_USERNAME`, `PRIMARY_USER_EMAIL`, and `PRIMARY_USER_PASSWORD` as a legacy bootstrap mechanism. They are optional for new installations.
