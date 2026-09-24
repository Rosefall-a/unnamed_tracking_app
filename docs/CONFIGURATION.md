# Central Configuration

The deployment and setup UI is generated from the backend configuration registry. The frontend does not maintain a second hard-coded list of setup fields.

The main components are:

- src/backend/src/core/config_registry.py — sections and field metadata.
- src/backend/src/core/env_handler.py — environment resolution, precedence, section/field status, validation, and startup policy.
- src/backend/src/api/routes/setup.py — exposes the schema and persists fields explicitly assigned to application storage.
- src/frontend/src/services/setup.ts — frontend representation of the backend schema.
- src/frontend/src/views/Setup.vue — generic renderer for the registry schema.

## Source ownership and visibility

Every registry field declares a source:

- ENV — deployment-owned. A value in the environment or .env is authoritative and the generated UI locks the field.
- SETUP — application-owned. The setup UI may provide it.
- BOTH — the UI may provide it, but an environment value always wins.

Resolution is:

    environment/.env
          |
          v
    persisted value
          |
          v
    registry default

This is why a half-complete `.env` file works correctly: fields supplied by the environment are populated and locked, while missing application-owned fields remain editable. The handler reads the process environment and discovers `.env` from the current directory/parents (or `ENV_FILE` when explicitly supplied), preventing the setup process from accidentally reading a different working directory than the application.

`visible` is separate from source ownership. An ENV-owned non-secret value such as `AUTH_COOKIE_SECURE` can be shown as its resolved value while remaining read-only. Sensitive deployment-only values can be hidden. Setup-owned secret inputs remain available for entering a new secret, but existing secret material is never returned.

## Sections and status

Each section has an ID, title, description, order, required/optional status, removal policy, visibility, and optional menu/default-selection metadata. `required=True` always forces a section to be selected; `default=True` selects an optional section initially, but the administrator can remove it on the Welcome screen. `menu` lets multiple sections share a future navigation/menu grouping without forcing them onto one setup page.

Current sections are:

- Database — required and deployment-owned.
- First administrator — required during first-run setup; account creation remains a bootstrap operation.
- API keys — optional.
- OpenID Connect / SSO — optional.

The handler calculates:

- not_configured
- partial
- configured
- completed_by_env
- blocked_by_env

A required ENV-only field that is missing makes its section `blocked_by_env`; the generated UI reports the missing variable and does not offer it as a setup input.

Required fields may be conditional. OIDC issuer/client ID/client secret are required only when the OIDC section is selected and OIDC is enabled.

## Field metadata

A registry field can declare:

- name
- section
- source
- input type: text, secret, boolean, integer, choice, URL, or email
- label
- description
- hint
- placeholder
- choices
- default and development/testing defaults
- required
- required_group (`group:variant`; all fields in a variant are required together, variants are alternatives)
- secret
- generated
- deprecated and deprecated_message
- visible
- heading (optional visual group within the section)
- storage ownership

The setup frontend consumes these properties directly. A normal new field should not require a field-specific change to Setup.vue.

### Field headings

`heading` groups fields visually without creating another setup page. Fields without a heading are rendered first. Headed fields are then grouped by heading in the order their first field appears. For example, the General section can put all size limits under `heading="Max sizes"` while leaving `DEBUG` under `heading="Debug mode"`; both remain on the same General page.

## Required configuration groups

`required=True` means an individual field is mandatory. `required_group` is for alternatives where one complete configuration form can satisfy a requirement. The syntax is `group:variant`:

```text
required_group="database:postgres"
required_group="database:url"
```

All fields in `database:postgres` must be configured together, while `database:url` is an alternative. The database requirement therefore becomes **PostgreSQL user + password + database OR DATABASE_URL**. This pattern is generic and can be reused for future configuration alternatives without adding special-case UI code.

## Generated and persisted SECRET_KEY

`SECRET_KEY` is intentionally marked `generated=True`, `secret=True`, and `visible=False`. When no deployment `SECRET_KEY` is supplied, `EnvConfigHandler` calls the persistent Fernet-key handler. That handler generates a cryptographically valid Fernet key and writes it to `APP_DATA_DIR/config/fernet.key`, plus two redundant copies (`fernet.key.1` and `fernet.key.2`), with restrictive file permissions. Subsequent starts recover the same key from those files, so encrypted application secrets and session signing remain stable across restarts. If a valid environment key is supplied, it is authoritative and is persisted as the installation key. The actual secret is never returned by the setup API.

## Adding a new environment variable

Use this procedure whenever a new deployment variable is introduced.

### 1. Add it to the registry

Add a ConfigSpec to CONFIG_REGISTRY:

    ConfigSpec(
        "MY_NEW_SETTING",
        "api_keys",
        source=ConfigSource.BOTH,
        input_type="choice",
        label="My new setting",
        choices=(("one", "One"), ("two", "Two")),
        default="one",
        hint="Choose the deployment mode.",
    )

Choose the source deliberately. Use ConfigSource.ENV when deployment operators must control the value through .env. Use BOTH or SETUP when the application is allowed to own it.

### 2. Decide visibility and secrecy

For a normal non-secret ENV variable, leave `visible=True`; it is shown but read-only. For an ENV-only secret, use `secret=True`; its value is never returned and the generated form hides it. For a setup-owned secret, use:

    input_type="secret"
    secret=True

Secret values are never returned to the browser. Use `visible=False` when the field itself should not appear. The schema only reports whether a secret is configured and whether the environment owns it.

### 3. Decide how it is persisted

If the setting is application-owned, add an explicit storage mapping to the appropriate database model and to _save_configuration() in setup.py.

Do not silently persist arbitrary registry fields. The explicit mapping is a security boundary.

If the setting is ENV-only, it normally does not need a database column.

### 4. Add validation and dependencies

If the new field changes whether another field is required, implement that relationship in EnvConfigHandler.

For example, OIDC requires issuer/client ID/client secret only while OIDC is enabled. When OIDC is disabled, partial provider data can be stored without enabling OIDC login.

### 5. Add it to example.env

Add a safe example:

    MY_NEW_SETTING=one

Never put real credentials in example.env.

### 6. Update documentation

Document:

- what the variable controls;
- whether it is ENV-only or editable;
- whether an environment value locks the UI;
- whether it is secret;
- its default;
- dependencies and validation.

Update docs/CONFIGURATION.md and, for user-facing setup changes, docs/SETUP.md.

### 7. Add focused tests

At minimum test environment resolution, partial configuration, requiredness, secret masking, environment locking, and dependency validation.

The maintenance rule is: registry first, handler second, persistence/validation third, documentation and tests last. The generic Vue setup component should normally require no field-specific change.

## Secrets and Fernet

Application-owned secrets saved by setup are encrypted with `encrypt_secret()` before database persistence. It uses `settings.SECRET_KEY`. A valid supplied `SECRET_KEY` is used directly; if omitted, the persistent Fernet-key handler generates a stable key under `APP_DATA_DIR/config/fernet.key` and maintains redundant copies. Existing ciphertext requires the same key, so changing it without the old key intentionally fails closed.

## OIDC enabled behavior


- When enabled, selecting OIDC for setup requires issuer URL, client ID, and client secret.
- When disabled, incomplete credentials are allowed and can be completed later.
- When disabled, OIDC login is not used.
- The OIDC section is selected by default, but remains removable because it is optional. If any OIDC environment variable is supplied, it is also surfaced automatically. If OIDC_ENABLED is supplied through .env, it is locked and wins over the database value.
- `OIDC_REDIRECT_URI` is generated from the current application URL and the `/api/auth/oidc/callback` route. It is displayed read-only in setup and is not accepted as a user-defined setup value. Runtime OIDC configuration also derives the redirect URI from the current request, so a stale saved URI cannot override the current address.
- Named OIDC providers similarly derive `/api/auth/oidc/callback/<provider-slug>` from the current request.

This is separate from named-provider controls such as enabled, show_on_login, and autostart_enabled.

## Deprecated configuration

Deprecated registry fields carry a `deprecated_message`. When a deprecated environment variable is supplied, startup logging emits that message, including the replacement to use. For example, `DATABASE_URL` points operators to `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.

## Frontend-only Vite configuration

VITE_USE_MOCK_DATA intentionally remains outside the backend registry. It is an early-stage frontend development/testing switch consumed directly by Vite through import.meta.env.VITE_USE_MOCK_DATA.

It remains documented in example.env, but it must not be exposed by /api/setup/configuration or treated as a normal application setting.

The TypeScript declaration is in src/frontend/src/vite-env.d.ts.

## Forced startup UI

Set STARTUP_UI=forced to keep /setup reachable after the first administrator exists.

The same registry schema is used. Environment-owned fields remain locked.

Forced mode never recreates or replaces the first administrator; it only exposes post-install configuration.

## Security rules

- Never return raw secret values from setup/configuration APIs.
- Never allow a request body to override an ENV-owned value.
- Do not duplicate defaults in Vue.
- Do not add real secrets to example.env.
- Keep first-admin creation separate from ordinary configuration.
