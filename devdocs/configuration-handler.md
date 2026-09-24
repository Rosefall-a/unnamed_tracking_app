# Configuration Handler Implementation Notes

## Architecture

The configuration system has three layers:

    Config registry
        |
        +-- sections
        +-- field types
        +-- labels/hints
        +-- defaults
        +-- requiredness
        +-- source ownership
        +-- storage ownership
        |
        v
    EnvConfigHandler
        |
        +-- .env + process environment
        +-- persisted values
        +-- field/section status
        +-- dependency validation
        |
        v
    /api/setup/configuration
        |
        v
    Setup.vue generic renderer

The frontend should not recreate configuration rules that already exist in the registry.

## Adding an environment variable

1. Add a ConfigSpec to CONFIG_REGISTRY.
2. Choose ConfigSource.ENV, SETUP, or BOTH.
3. Choose the UI type: text, secret, boolean, integer, choice, URL, or email.
4. Add label, description, hint, placeholder, and choices as appropriate.
5. Mark secrets with secret=True.
6. If application-owned, add an explicit persistence mapping.
7. Add dependency validation in EnvConfigHandler when requiredness depends on it.
8. Add a safe entry to example.env.
9. Update docs/CONFIGURATION.md and docs/SETUP.md.
10. Add a focused backend test.

Do not add a normal field directly to Setup.vue.

## Environment precedence

The handler uses:

    environment/.env > persisted database value > registry default

An environment-owned field is returned with:

- locked: true
- source: env
- configured: true

For secrets the value is always null. This prevents the setup endpoint from becoming a secret-disclosure endpoint.

## Section state

The backend returns:

- not_configured
- partial
- configured
- completed_by_env

The first-run frontend uses these states to select optional sections automatically. Required sections cannot be removed.

## First administrator

The first administrator is deliberately special. The registry describes its fields, but the handler does not create users. POST /api/setup performs bootstrap account creation after configuration has been accepted.

When all bootstrap values are supplied by the environment, the browser does not need to receive the password. The backend reads it directly from EnvConfigHandler.

## Forced startup UI

STARTUP_UI=forced keeps /setup reachable after the first administrator exists.

The configuration endpoint remains the same, so there is only one setup UI contract. Forced mode uses PUT /api/setup/configuration and is protected by the normal admin dependency. It never calls the first-admin creation path.

## OIDC

OIDC_ENABLED defaults to true.

When enabled, issuer/client ID/client secret are required if the OIDC section is selected. When disabled, partial provider values can be stored without enabling OIDC login.

Environment values still override the database setting.

## Frontend-only Vite setting

VITE_USE_MOCK_DATA is intentionally not returned by the backend registry schema. It is an early-stage frontend development switch read directly through import.meta.env. Its TypeScript declaration lives in src/frontend/src/vite-env.d.ts.

## Security rules

- Never return raw secret values.
- Never let a request override an environment-owned field.
- Never duplicate field defaults in Vue.
- Keep persistence mappings explicit.
- Keep bootstrap account creation separate from ordinary configuration.
