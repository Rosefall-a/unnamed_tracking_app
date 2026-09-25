# Setup and Deployment

Unnamed Tracking App has a production Docker image and a separate development Compose stack.

## First setup

The setup UI is generated from the backend configuration registry. Environment-owned values are resolved and locked, while application-owned values can be persisted through setup.

The first administrator can be supplied through the bootstrap environment variables or created through the normal setup flow.

## Production Compose

The production Compose file is src/docker-container/compose.yaml.

The current file requires POSTGRES_PASSWORD, SECRET_KEY, and PRIMARY_USER_PASSWORD. It defaults POSTGRES_USER and POSTGRES_DB to unnamed_tracking, maps host port 8080 to container port 80, and persists application data at ./data:/data.

PostgreSQL uses a named pgdata volume.

See [Production Docker Image](../deployment/production-docker.md) for the complete deployment configuration and startup behavior.

## Development Compose

The root compose.yaml runs PostgreSQL, the backend, and the frontend separately. The frontend is exposed on port 5173.

Use [Installation](installation.md) for development startup commands.
