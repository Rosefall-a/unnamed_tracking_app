# Authentication

## First-run setup

A new database has no users. The web setup flow creates the first administrator and establishes a normal application session.

Legacy `PRIMARY_USER_USERNAME`, `PRIMARY_USER_EMAIL` and `PRIMARY_USER_PASSWORD` can still bootstrap the first user when all three are populated.

## Local authentication

The application uses server-side user sessions stored in the database. The browser receives an HTTP-only session cookie.

The cookie is affected by `AUTH_COOKIE_SECURE`; enable that flag when the public application is served over HTTPS.

## API keys

User API keys begin with `utk_`. They are intended for programmatic integrations such as the Playnite extension.

API-key authentication is distinct from the browser session. The Playnite extension sends:

```http
Authorization: Bearer utk_<secret>
```

## OIDC / SSO

OIDC is implemented as a backend authorization-code flow.

Configuration can come from deployment Settings in PostgreSQL or from the backwards-compatible `OIDC_*` environment fallback.

The current callback requires:

- a `sub` claim
- an email claim

The current code **does not reject an explicitly unverified email claim**. The old verification check is commented out in the callback. This differs from the wording in the current `docs/OIDC.md` and `docs/SETUP.md), which still describe verified email as mandatory and should be corrected in a documentation follow-up.

Users can be matched by configured email or username. Existing linked OIDC subjects remain bound to their local account. Optional group membership can control administrator status.

## OIDC secrets

Client secrets are sent to the backend and encrypted before database persistence. They are not intended to be placed in frontend variables.

## Session lifetime

The opaque application session has a server-defined TTL in the authentication code. A future configuration pass should make any intended session lifetime configuration explicit rather than implying it is controlled by `.env` when it is not.

## Security expectations

- Use HTTPS in production.
- Keep `SECRET_KEY` stable.
- Do not log authorization codes, tokens, passwords or client secrets.
- Keep API keys and OIDC secrets out of source control.
