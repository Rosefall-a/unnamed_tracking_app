# Setup and Deployment

Unnamed Tracking App has a production Docker image and a separate development Compose stack.

## First setup

The setup UI is generated from the backend configuration registry. Environment-owned values are resolved and locked, while application-owned values can be persisted through setup.

The first administrator can be supplied through the bootstrap environment variables or created through the normal setup flow.

OIDC is configured after installation from **Settings → OIDC / SSO**. See the [OIDC user guide](../user-guide/oidc.md) rather than the first-run setup documentation for that configuration.

## Production Compose

The production Compose file is \`src/docker-container/compose.yaml\`.

The current file requires \`POSTGRES_PASSWORD\`, \`SECRET_KEY\`, and \`PRIMARY_USER_PASSWORD\`. It defaults \`POSTGRES_USER\` and \`POSTGRES_DB\` to \`unnamed_tracking\`, maps host port 8080 to container port 80, and persists application data at \`./data:/data\`.

PostgreSQL uses a named \`pgdata\` volume.

See [Production Docker Image](../deployment/production-docker.md) for the complete deployment configuration and startup behavior.

## Development Compose

The root \`compose.yaml\` runs PostgreSQL, the backend, and the frontend separately. The frontend is exposed on port 5173.

Use [Installation](installation.md) for development startup commands.

## Environment-managed configuration

Deployment-owned settings can be supplied through environment variables. Such values can be locked from the application UI.

See [Environment Variables](environment-variables.md) and [Configuration](configuration.md) for the supported variables and ownership/precedence rules.
