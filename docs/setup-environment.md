# Setup environment overrides

The setup system supports declarative environment variables using a double-underscore tree.

Example:

    OIDC__AUTHENTIK__NAME=Authentik
    OIDC__AUTHENTIK__ISSUER_URL=https://auth.example.com
    OIDC__AUTHENTIK__CLIENT_ID=archive
    OIDC__AUTHENTIK__CLIENT_SECRET=replace-me
    OIDC__AUTHENTIK__SHOW_ON_LOGIN=true
    OIDC__AUTHENTIK__AUTOSTART_ENABLED=true

The first component selects a setup page, the second selects a named object on that
page, and the final component selects a field. Environment values are authoritative
and must not be overwritten by values submitted from the setup browser.

## Setup mode

- SETUP_MODE=auto (default): interactive setup is available when setup is required.
- SETUP_MODE=dev: interactive setup remains available for development.
- SETUP_MODE=false: disables the interactive setup surface for environment-only deployments.

Disabling the UI does not disable environment configuration.

## Persistent Fernet key

If SECRET_KEY is not supplied, the application generates a Fernet key and stores
redundant copies below APP_DATA_DIR/config (default /data/config). This keeps
encrypted settings stable across container restarts.

To supply an explicit key:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Keep the key secret. Losing it means encrypted deployment credentials cannot be
decrypted.

## Deployment backup downloads

Deployment-secret downloads are disabled by default. The intended deployment
setting is:

    ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD=false

Only explicitly enabling that setting should expose a direct browser download of
deployment-secret backups; server-side setup copies remain available to the setup flow.
