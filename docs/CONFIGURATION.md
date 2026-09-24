# Central Configuration

The central configuration boundary is built around `EnvConfigHandler` and the declarative registry. It resolves deployment inputs, generated secrets, defaults, and dependency-aware validation. It deliberately does not own user accounts.

## Source policy

- **ENV** — deployment-owned and unavailable to the setup page.
- **SETUP** — application-owned and configured through setup/settings.
- **BOTH** — setup may provide it, but an environment value always wins.

`VITE_USE_MOCK_DATA` is ENV-only. `SECRET_KEY` is also deployment-owned; when omitted, it is generated and persisted under `APP_DATA_DIR/config`.

## Fernet lifecycle

The persistent Fernet implementation keeps three `0600` copies. A missing single copy is repaired from the valid majority. If valid copies disagree, startup fails closed. If no valid key exists and no environment key was supplied, a new key is generated and persisted. Restore and rotation retain the previous key for recovery.

## Database configuration

New deployments use `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, and `POSTGRES_PORT`. The runtime still constructs an internal SQLAlchemy URL. `DATABASE_URL` remains a compatibility path and is deprecated for new deployments.

## Dependency validation

- A partial database component set is an unrecoverable error.
- A partial primary-user set is an unrecoverable error.
- An OIDC issuer without client ID/secret is an unrecoverable error.
- Missing recommended OIDC scopes produce a warning.
- Invalid `STARTUP_MODE` is an unrecoverable error.

The design intentionally distinguishes something that cannot start safely from something an administrator can correct or ignore.

## Startup modes

`STARTUP_MODE` is ENV-only:
- empty/unset: ordinary defaults only;
- `development`: disposable development defaults, including initial-admin inputs;
- `testing`: reduced test-oriented defaults.

The handler only supplies the initial-admin inputs. Existing authentication/setup code remains responsible for creating the account, hashing the password, and creating the session.

## Startup vs setup

The startup page remains separate from the setup page. Startup validates whether the deployment can safely become ready and records warnings/errors before database readiness and backend health. Setup configures a new installation and can consume `/api/setup/configuration` for backend-owned defaults and source metadata without receiving secrets.

## Future hardening

`application_url` is intentionally deferred. It can later become a central origin/redirect security setting without changing the handler architecture.

`VITE_API_BASE_URL` is not part of the registry because the current frontend uses relative `/api` requests and the development proxy.