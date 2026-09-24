# Self-hosted setup

The setup page is generated from the backend configuration registry. It starts with a Welcome to setup screen, keeps required sections automatically, and lets the administrator add or remove optional sections such as API keys and OIDC.

## Setup flow

1. The frontend requests /api/setup/status and /api/setup/configuration.
2. The backend builds the schema from CONFIG_REGISTRY.
3. Environment values are resolved first.
4. Environment-owned fields are populated and locked when visible.
5. Sensitive deployment-only fields are hidden.
6. Persisted application values are used for fields not owned by the environment.
7. The welcome screen selects required sections and optional sections that already contain configuration.
8. The user can add or remove optional sections.
9. The generic renderer displays fields according to their registry type.
10. On first setup, selected configuration is saved and the first administrator is created.
11. With STARTUP_UI=forced, the same UI is available after installation and only saves configuration; it cannot create another administrator.

Secrets are never returned. A configured secret appears as a configured field with an empty password input.

## Missing .env values

`ConfigSource.ENV` fields are deployment-owned and cannot be completed from setup. If a required ENV-only value is missing, the section is marked **Needs .env**, the Welcome page displays a prominent warning with the missing variable, and Continue is disabled. This prevents PostgreSQL variables such as `POSTGRES_USER` from being incorrectly presented as setup inputs.

## Environment precedence

A partially configured environment is supported. For example:

    OIDC_ISSUER_URL=https://login.example.com/realms/archive
    OIDC_CLIENT_ID=archive
    # OIDC_CLIENT_SECRET is omitted

The setup page shows the issuer and client ID from .env as locked fields. The missing client secret remains editable and, when OIDC is enabled, required.

## Secrets and Fernet encryption

Secrets saved through setup are encrypted before database persistence with the Fernet key from `SECRET_KEY`. A valid deployment-provided key is used directly; otherwise a stable key is generated and persisted under `APP_DATA_DIR/config/fernet.key` with redundant copies. Plaintext secret values are never returned by the setup API.

## OIDC

OIDC is optional. Its master switch defaults to enabled when the OIDC section is selected.

If OIDC is enabled, issuer URL, client ID, and client secret are required.

If OIDC is disabled, partially entered provider values are allowed to be saved. This is useful when an administrator wants to enter the non-secret parts before obtaining a client secret. OIDC login remains disabled until the master switch is enabled and a usable provider exists.

Settings → OIDC / SSO continues to provide named providers, ordering, login presentation, login visibility, and autostart controls.

## Example .env

Copy example.env to .env and replace placeholders:

    POSTGRES_USER=archive
    POSTGRES_PASSWORD=change-this-database-password
    POSTGRES_DB=archive
    POSTGRES_HOST=db
    POSTGRES_PORT=5432

    # Optional: keep /setup available after installation.
    # STARTUP_UI=forced

    # Optional OIDC deployment ownership.
    # OIDC_ENABLED=true
    # OIDC_ISSUER_URL=https://login.example.com/realms/archive
    # OIDC_CLIENT_ID=archive
    # OIDC_CLIENT_SECRET=replace-me
    # OIDC_SCOPES=openid profile email
    # OIDC_GROUPS_CLAIM=groups
    # OIDC_ADMIN_GROUP=archive-admins
    # OIDC_USER_MATCH_FIELD=email

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
- OIDC is marked partial and selected automatically when any OIDC environment value is present.

### OIDC disabled

Select OIDC, turn Enable OIDC off, enter only an issuer URL, and save. The partial provider data should be accepted and OIDC login should remain disabled.

### Forced setup

After creating the administrator, set:

    STARTUP_UI=forced

and restart. Open /setup. The same dynamic configuration screen should appear, but no administrator fields should be recreated or submitted as a new account.

### Frontend mock mode

Set:

    VITE_USE_MOCK_DATA=true

and rebuild the frontend. Mock scan/settings data should be used. This variable is an early-stage frontend development feature and is intentionally not editable from the backend setup page.

No SMTP configuration is part of this configuration work.
