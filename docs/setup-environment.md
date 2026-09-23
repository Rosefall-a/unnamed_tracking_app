# Setup environment overrides

The setup system supports declarative environment variables using a double-underscore tree.

Example:

OIDC__AUTHENTIK__NAME=Authentik
OIDC__AUTHENTIK__ISSUER_URL=https://auth.example.com
OIDC__AUTHENTIK__CLIENT_ID=archive
OIDC__AUTHENTIK__CLIENT_SECRET=replace-me

The first component selects a setup page, the second selects a named object on that page, and later components select fields. Environment values are authoritative over values submitted by the setup browser.

## Setup mode

SETUP_MODE=auto keeps interactive setup available when setup is required.

SETUP_MODE=dev keeps interactive setup available for development.

SETUP_MODE=false disables the interactive setup surface for environment-only deployments. Disabling the UI does not disable environment configuration.

## Persistent encryption key

If SECRET_KEY is not supplied, the application generates and persists a Fernet key under the application data directory. The persistent key must survive container recreation because it protects encrypted application secrets.

## Deployment backup downloads

Direct browser downloads of deployment-secret archives are disabled unless ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD=true. Server-side setup-path copies remain available to the restore flow.

## Extending setup

New setup pages should register a stable namespace, consume overrides at the save boundary, expose only a sanitized environment tree to the frontend, and document every variable under docs.
