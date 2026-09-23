# Setup environment overrides

The setup system supports declarative environment variables using a double-underscore tree.

Example:
```dotenv
OIDC__AUTHENTIK__NAME=Authentik
OIDC__AUTHENTIK__ISSUER_URL=https://auth.example.com
OIDC__AUTHENTIK__CLIENT_ID=archive
OIDC__AUTHENTIK__CLIENT_SECRET=replace-me
OIDC__AUTHENTIK__SHOW_ON_LOGIN=true
OIDC__AUTHENTIK__AUTOSTART_ENABLED=true
```
The first component selects a setup page, the second selects a named object, and later components select fields. Environment values are authoritative over setup-form values.

`SETUP_MODE=auto` keeps interactive setup available when required. `SETUP_MODE=dev` keeps it available for development. `SETUP_MODE=false` disables the interactive setup surface for environment-only deployments.

If `SECRET_KEY` is omitted, a persistent Fernet key is generated under the application data directory. Preserve that data across redeployments.

Direct browser downloads of deployment-secret backups are disabled unless `ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD=true`. `APPLICATION_JSON_PATH` selects the persistent setup backup path and defaults to `/data/application.json`.


## Database environment

The backend accepts either `DATABASE_URL` or the standard PostgreSQL variables `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`. When `DATABASE_URL` is omitted, it builds a `postgresql+psycopg` URL using `POSTGRES_HOST` (default `db`) and `POSTGRES_PORT` (default `5432`). Docker Compose passes the same `POSTGRES_*` values to PostgreSQL and the backend, so a normal deployment does not need to duplicate the database URL.
