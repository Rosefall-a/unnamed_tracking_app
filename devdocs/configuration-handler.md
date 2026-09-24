# Configuration Handler Implementation Notes

## Components

- `src/core/config_registry.py` — declarative metadata and source policy.
- `src/core/env_handler.py` — environment/.env resolution, startup modes, setup-safe metadata, dependency validation, and initial-admin bootstrap inputs.
- `src/core/fernet_key.py` — persistent Fernet generation, redundancy, restore, and rotation.
- `src/core/config.py` — Pydantic runtime settings and database URL compatibility.
- `src/api/routes/setup.py` — exposes non-secret configuration metadata to setup.
- `src/docker-container/entrypoint.sh` — validates configuration before PostgreSQL readiness and records warnings in startup diagnostics.

## Resolution flow

```text
environment / .env
        |
        v
Config Registry -> source policy + defaults + requirements
        |
        v
EnvConfigHandler
   |          |
   |          +--> dependency issues
   |                 |-- warning: recoverable
   |                 `-- error: unrecoverable
   |
   +--> generated/persistent SECRET_KEY
   +--> setup-safe schema
   `--> runtime configuration
```

The handler does not write users, sessions, OIDC provider rows, or other database entities.

## Initial administrator bootstrap

The handler has a small bootstrap role: it resolves the three initial-admin inputs and reports their completeness. It does not create the account. Existing authentication/setup code remains authoritative for hashing, database writes, sessions, and administrator promotion.

## Dependency tree

```text
database
  `-- required for runtime

OIDC issuer
  |-- client id
  |-- client secret
  `-- recommended scopes
       |-- openid
       |-- profile
       `-- email

primary user
  |-- username
  |-- email
  `-- password
```

The long-term design should move dependency relationships into registry metadata instead of accumulating unrelated validators.

## Setup/startup contract

The setup endpoint returns configuration name, source policy, non-secret default, required/generated/secret flags, description, and active startup mode. It never returns raw secret values.

The same issue model is suitable for the startup page, preventing Vue setup and startup scripts from implementing different validation rules.

## Database URL transition

The external deployment contract is moving to individual PostgreSQL variables:

```text
POSTGRES_USER + POSTGRES_PASSWORD + POSTGRES_DB
                 |
                 v
        central handler/config
                 |
                 v
       internal DATABASE_URL
```

`DATABASE_URL` remains accepted temporarily for compatibility. New examples and startup diagnostics prefer the individual variables.

## Maintenance rules

1. Add configuration to the registry first.
2. Choose ENV/SETUP/BOTH ownership explicitly.
3. Define defaults and startup-mode behavior.
4. Mark secret/generated values.
5. Add dependency validation.
6. Expose only non-secret metadata to setup.
7. Update `/docs` and `/devdocs`.
8. Add focused tests before unrelated configuration work.

Do not duplicate a default across Vue, example.env, startup scripts, and backend validators when it can be derived from the registry.

## Test matrix

Use a fresh database for each setup-path test where practical.

- **Minimal:** only PostgreSQL variables. Setup should expose normal editable account fields.
- **OIDC from ENV:** add `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`. The setup UI should populate and lock those fields.
- **OIDC defaults from ENV:** also set scopes/groups/matching/admin-group values and verify they are populated.
- **Forced UI:** add `STARTUP_UI=forced` after setup is complete. Restart and open `/setup`; it should remain available and show resolved deployment values.
- **Named OIDC:** use Settings → OIDC / SSO to create two providers, reorder them, toggle login visibility, and test each generated `/login/<slug>` URL.
- **Invalid dependency:** remove one OIDC credential while leaving the issuer configured. Verify startup reports the dependency error.

No SMTP configuration is part of this release's setup flow.
