# Setup

The easiest way to run Unnamed Tracking App is with Docker Compose.

## Requirements

You will need:

- Docker
- Docker Compose
- A directory where the application data can be stored

## 1. Download the example Compose file

The repository includes an example Compose file at `example-docker-compose.yaml`.

Copy it to your deployment directory:

```bash
cp example-docker-compose.yaml compose.yaml
```

On Windows, you can also copy the file manually using File Explorer.

## 2. Create your environment file

Create a `.env` file in the same directory as your Compose file.

The Compose configuration requires `POSTGRES_PASSWORD` to be set. The remaining application and database settings can be configured through the environment variables documented in the [Environment Variables](../environment-variables.md) page.

For example:

```dotenv
POSTGRES_PASSWORD=change-this-password
```

Use a strong, unique password for a real deployment.

## 3. Example Compose configuration

The following is the repository's example Compose configuration:

```yaml
services:
  app:
    image: ghcr.io/rosefall-a/unnamed_tracking_app:feat-central-config-handler
    restart: unless-stopped
    ports:
      - "${UNNAMED_TRACKING_APP_PORT:-8080}:80"
    env_file:
      - .env
    volumes:
      - ./data:/data

  db:
    image: postgres:18
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-unnamed_tracking}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}
      POSTGRES_DB: ${POSTGRES_DB:-unnamed_tracking}
    volumes:
      - pgdata:/var/lib/postgresql
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-unnamed_tracking} -d ${POSTGRES_DB:-unnamed_tracking}" ]
      interval: 5s
      timeout: 5s
      retries: 20

volumes:
  pgdata:
```

## 4. Start the application

From the directory containing `compose.yaml` and `.env`, run:

```bash
docker compose up -d
```

Check the containers with:

```bash
docker compose ps
```

To view application logs:

```bash
docker compose logs -f app
```

## 5. Open the application

By default, the example Compose file exposes the application on port `8080`.

Open:

```text
http://your-server:8080
```

If you changed `UNNAMED_TRACKING_APP_PORT`, use that port instead.

## Updating

To update the application image:

```bash
docker compose pull
docker compose up -d
```

Check the release or deployment documentation for the appropriate image tag before updating a production installation.

## Stopping the application

To stop the containers without removing them:

```bash
docker compose stop
```

To stop and remove the containers:

```bash
docker compose down
```

Your named PostgreSQL volume and bind-mounted application data are retained when using `docker compose down`.

## Next steps

- See [Environment Variables](../environment-variables.md) for available configuration options.
- See [API Documentation](../development/api.md) for the automatically generated API documentation.
