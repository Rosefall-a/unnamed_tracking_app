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
        +-- visibility/secrecy
        +-- storage ownership
        |
        v
    EnvConfigHandler
        |
        +-- .env + process environment
        +-- persisted values
        +-- field/section status
        +-- dependency validation
        +-- startup policy
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
5. Mark secrets with secret=True and choose visible separately when the field itself should be hidden.
6. If application-owned, add an explicit persistence mapping.
7. Add dependency validation in EnvConfigHandler when requiredness depends on it.
8. Add a safe entry to example.env.
9. Update docs/CONFIGURATION.md and docs/SETUP.md.
10. Add a focused backend test.

Do not add a normal field directly to Setup.vue.

## Environment precedence

The effective precedence is:

    process environment
          >
    .env
          >
    persisted application configuration
          >
    startup-mode default
          >
    registry default

Process environment values override values loaded from .env. The handler's environment resolution is field-based, so an environment value locks only that field; missing application-owned values can still be supplied through setup.

Environment-owned fields are returned with:

- locked: true
- source: env
- configured: true when supplied
- env_only: true for ConfigSource.ENV
- visible: false for sensitive deployment-only fields

A required ENV-only field that is absent blocks its section with `blocked_by_env`; the setup page directs the operator back to .env rather than asking for the value in setup.

For secrets the value is always null. This prevents the setup endpoint from becoming a secret-disclosure endpoint.

## Startup policy

`STARTUP_MODE` is the only operator-facing startup policy.

- `dev` or `development`: development defaults and no post-install setup/configuration UI.
- `testing`: setup/configuration UI is shown. Testing-specific defaults are used when defined; otherwise development defaults are used, then normal defaults.
- empty or any other value: setup/configuration UI is shown and normal defaults are used.

The backend exposes the derived `startup_ui_enabled` status to the frontend. The frontend should consume that policy rather than interpreting mode aliases itself. There is deliberately no `STARTUP_UI` setting.

## Section state

The backend returns:

- not_configured
- partial
- configured
- completed_by_env
- blocked_by_env

The first-run frontend uses these states to select optional sections automatically. Required sections cannot be removed.

## First administrator

The first administrator is deliberately special. The registry describes its fields, but the handler does not create users. POST /api/setup performs bootstrap account creation after configuration has been accepted.

When all bootstrap values are supplied by the environment, the browser does not need to receive the password. The backend reads it directly from EnvConfigHandler.

## OIDC

Selecting OIDC means it is being configured. Issuer URL, client ID, and client secret are required when the OIDC section is selected, and a complete provider is enabled automatically when setup saves it. There is no separate OIDC enable switch in the generated setup flow.

The setup redirect URI is generated from the current request URL and displayed read-only. It is not accepted as a user-defined setup value. Named providers derive their callback from the current request and provider slug as well.

Environment-provided OIDC values remain authoritative and lock their corresponding fields. Secrets remain masked.

## Frontend-only Vite setting

`VITE_USE_MOCK_DATA` is intentionally not returned by the backend registry schema. It is an early-stage frontend development switch read directly through import.meta.env. Its TypeScript declaration lives in src/frontend/src/vite-env.d.ts.

## Fernet encryption

Setup-owned secrets are encrypted with `encrypt_secret()` before persistence using `settings.SECRET_KEY`. A supplied key is used directly; otherwise the persistent key handler generates and stores a stable key under `APP_DATA_DIR/config/fernet.key` with redundant copies.

Deprecated environment variables are logged at startup with their registry-provided replacement message.

## Security rules

- Never return raw secret values.
- Never let a request override an environment-owned field.
- Never duplicate field defaults in Vue.
- Keep persistence mappings explicit.
- Keep bootstrap account creation separate from ordinary configuration.
