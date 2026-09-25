# Self-hosted setup

The setup page is generated from the backend configuration registry. It starts with a Welcome to setup screen, keeps required sections automatically, and lets the administrator add or remove optional sections such as API keys and OIDC.

## Setup flow

1. The frontend requests /api/setup/status and /api/setup/configuration.
2. The backend builds the schema from CONFIG_REGISTRY.
3. Environment values are resolved first.
4. Environment-owned fields are populated and locked when visible.
5. Sensitive deployment-only fields are hidden.
6. Persisted application values are used for fields not owned by the environment.
7. The welcome screen selects required sections, registry-default-selected sections, and optional sections that already contain configuration.
8. The user can add or remove optional sections; `required` overrides `default`, so required sections cannot be removed.
9. The generic renderer displays fields according to their registry type.
10. On first setup, selected configuration is saved and the first administrator is created.
11. Startup behavior follows `STARTUP_MODE`. In `dev`/development mode, the setup/configuration UI is skipped after installation. In `testing` mode, the UI is shown and development defaults are used unless a testing-specific default exists. In normal mode (empty or unrecognized value), the UI is shown and normal defaults are used. After the first administrator exists, the page is a configuration editor and saving requires an authenticated administrator.

Secrets are never returned. A configured secret appears as a configured field with an empty password input.

## Missing .env values

`ConfigSource.ENV` fields are deployment-owned and cannot be completed from setup. If a required ENV-only value is missing, the section is marked **Needs .env**, the Welcome page displays a prominent warning with the missing variable, and Continue is disabled. This prevents PostgreSQL variables such as `POSTGRES_USER` from being incorrectly presented as setup inputs.

## Environment precedence

The effective precedence is process environment > `.env` > persisted application configuration > startup-mode default > registry default. A partially configured environment is supported. For example:

    OIDC_ISSUER_URL=https://login.example.com/realms/archive
    OIDC_CLIENT_ID=archive
    # OIDC_CLIENT_SECRET is omitted

The setup page shows the issuer and client ID from .env as locked fields. The missing client secret remains editable and required when the OIDC section is selected.

## Secrets and Fernet encryption

Secrets saved through setup are encrypted before database persistence with the Fernet key from `SECRET_KEY`. A valid deployment-provided key is used directly; otherwise a stable key is generated and persisted under `APP_DATA_DIR/config/fernet.key` with redundant copies. The generated key is restored on later starts, so omitting `SECRET_KEY` does not create a new encryption/session key on every restart. Plaintext secret values are never returned by the setup API.

## OIDC

OIDC is optional and is selected by default on the Welcome screen. It can still be removed because it is not required. Selecting the OIDC section means it is being configured; there is no separate OIDC enable switch in setup.

When OIDC is selected, issuer URL, client ID, and client secret are required. A complete provider is enabled automatically when setup saves it.

The redirect URI is not user-entered. Setup displays a read-only URI generated from the address currently used to access the application (`/api/auth/oidc/callback`). Named providers use the same rule with their provider slug. This prevents setup from retaining a redirect URI copied from a different hostname or deployment.

Settings → OIDC / SSO continues to provide named providers, ordering, login presentation, login visibility, and autostart controls.

## Startup modes

`STARTUP_MODE` controls both the default profile and whether the startup configuration UI is shown:

- `dev` or `development`: use development defaults and skip the setup/configuration UI after installation.
- `testing`: show the setup/configuration UI; use a testing-specific default when one is defined, otherwise fall back to the development default, then the normal default.
- Empty or any other value: show the setup/configuration UI and use normal defaults.

Explicit values from the process environment or `.env` still override these mode defaults. Values entered or changed in the setup UI can override defaults for configuration that is owned by setup.

There is no separate startup-UI environment variable.

## Example .env

Copy example.env to .env and replace placeholders:

    POSTGRES_USER=archive
    POSTGRES_PASSWORD=change-this-database-password
    POSTGRES_DB=archive
    POSTGRES_HOST=db
    POSTGRES_PORT=5432

    # Startup profile. Leave empty for normal behavior.
    STARTUP_MODE=

    # Optional OIDC deployment ownership.
    # OIDC_ISSUER_URL=https://login.example.com/realms/archive
    # OIDC_CLIENT_ID=archive
    # OIDC_CLIENT_SECRET=replace-me
    # OIDC_SCOPES=openid profile email
    # OIDC_GROUPS_CLAIM=groups
    # OIDC_ADMIN_GROUP=archive-admins
    # OIDC_USER_MATCH_FIELD=email
    # OIDC_REDIRECT_URI is intentionally not configured: it is generated from the current request.

    # Frontend-only early-stage development switch.
    VITE_USE_MOCK_DATA=false

Keep the real .env out of source control.

## Adding configuration

For a new environment variable, follow the complete procedure in docs/CONFIGURATION.md under “Adding a new environment variable”.

A normal field should be added to the registry rather than hard-coded into Setup.vue.

## Validation checklist

### Fresh minimal installation

Use only the required PostgreSQL values. Confirm:

- Welcome to setup appears.
- Database is marked completed by environment when its required values are supplied.
- First administrator remains required.
- API keys and OIDC are optional.
- Continue can be pressed to reach the configuration sections; final submission still validates the first administrator.

### Partial environment configuration

Set only some OIDC variables. Confirm:

- supplied values are populated;
- supplied values are locked;
- missing values remain editable;
- OIDC is selected by default, and remains selected automatically when any OIDC environment value is present;
- the redirect URI is displayed but cannot be edited.

### Default selection and headings

Confirm optional sections marked `default=True` start selected but can be removed, while required sections remain selected regardless of their default. Confirm fields without `heading` appear first and fields sharing the same heading are grouped under one heading without creating additional pages.

#### Startup mode checks

After creating the administrator, verify each mode:

- `STARTUP_MODE=dev` skips /setup and uses development defaults.
- `STARTUP_MODE=testing` opens /setup and uses testing defaults where defined, otherwise development defaults.
- An empty or unrecognized `STARTUP_MODE` opens /setup and uses normal defaults.

Confirm an explicit value in `.env` still populates the corresponding field and takes precedence over the mode default.

## Frontend mock mode

Set:

    VITE_USE_MOCK_DATA=true

and rebuild the frontend. Mock scan/settings data should be used. This variable is an early-stage frontend development feature and is intentionally not editable from the backend setup page.

No SMTP configuration is part of this configuration work.
