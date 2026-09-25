# Setup with Arcane

The easiest way to deploy Unnamed Tracking App with Arcane is to create a new Compose stack and paste the Compose configuration and environment variables directly into Arcane.

Arcane provides two text areas for a Compose stack:

- **Compose** — paste the Docker Compose configuration here.
- **Environment** — paste the environment variables here.

You do **not** need to create an `.env` file manually when using Arcane.

## Requirements

You will need:

- A server running Docker
- [Arcane](https://getarcane.app/) installed and connected to your Docker host
- A directory on the Docker host where application data can be stored

## 1. Create a new stack in Arcane

Open Arcane and create a new Compose stack.

Give the stack a name such as:

`unnamed-tracking-app`

When Arcane shows the Compose and Environment text boxes, use the configurations below.

## 2. Compose configuration

Paste the following into Arcane's **Compose** text box:

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

## 3. Environment variables

Paste the following into Arcane's **Environment** text box.

You can change the values that you want to customize. At minimum, set a strong value for `POSTGRES_PASSWORD`.

```dotenv
# PostgreSQL deployment inputs. New deployments should use these instead of DATABASE_URL.
POSTGRES_USER=archive
POSTGRES_PASSWORD=change-this-database-password
POSTGRES_DB=archive
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Startup profile:
#   dev/development = development defaults, skip setup UI after installation
#   testing = show setup UI, use testing defaults where defined, otherwise development defaults
#   empty/anything else = show setup UI and use normal defaults
STARTUP_MODE=

# SECRET_KEY is deployment-owned. If omitted, the application generates and
# persists a stable Fernet key under APP_DATA_DIR/config.
SECRET_KEY=

AUTH_COOKIE_SECURE=false
DEBUG=false
MAX_UPLOAD_SIZE_MB=15
MAX_SAVE_ARCHIVE_SIZE_MB=4096
MAX_CLIP_SIZE_MB=500
MAX_WORLD_SAVE_SIZE_MB=2000

# Frontend-only early-stage development/testing switch. It is consumed by Vite,
# remains outside the backend configuration registry, and is intentionally not
# editable through /setup.
VITE_USE_MOCK_DATA=false

# Optional deployment-wide provider credentials. Values supplied here are
# authoritative and will be shown as locked fields by /setup.
STEAMGRIDDB_API_KEY=
RETROACHIEVEMENTS_API_KEY=
GIANTBOMB_API_KEY=
IGDB_CLIENT_ID=
IGDB_CLIENT_SECRET=
TMDB_API_KEY=
OMDB_API_KEY=
TVDB_API_KEY=
SCREENSCRAPER_DEVID=
SCREENSCRAPER_DEVPASSWORD=
SCREENSCRAPER_SSID=
SCREENSCRAPER_SSPASSWORD=
XBOX_CLIENT_ID=
XBOX_CLIENT_SECRET=

OIDC_ISSUER_URL=
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=
# OIDC_REDIRECT_URI is generated automatically from the URL used to access the application.
OIDC_SCOPES=openid profile email
OIDC_GROUPS_CLAIM=groups
OIDC_ADMIN_GROUP=
OIDC_USER_MATCH_FIELD=email

# Legacy compatibility only; prefer the three POSTGRES_* variables above.
# DATABASE_URL=postgresql+psycopg://archive:change-this-database-password@db:5432/archive

# Legacy first-user bootstrap. The normal setup UI is preferred.
# PRIMARY_USER_USERNAME=admin
# PRIMARY_USER_EMAIL=admin@example.com
# PRIMARY_USER_PASSWORD=Change-this-during-setup
```

### Important values to change

Before deploying, review these values:

- **`POSTGRES_PASSWORD`** — change this to a strong, unique database password.
- **`SECRET_KEY`** — optional. If left empty, the application generates and persists its own key.
- **`AUTH_COOKIE_SECURE`** — set this appropriately when the application is served over HTTPS.
- **Provider API keys** — only configure these if you want the corresponding integrations.
- **OIDC settings** — only configure these if you are using an OpenID Connect provider such as Authentik.

See [Environment Variables](../environment-variables.md) for a description of the available variables.

## 4. Deploy the stack

After entering both the Compose and Environment configurations, deploy/start the stack from Arcane.

Arcane will create the application and PostgreSQL containers and manage the Compose stack for you.

## 5. Open the application

The example Compose configuration exposes the application on port `8080`.

Open:

```text
http://your-server:8080
```

If you need a different host port, change the `UNNAMED_TRACKING_APP_PORT` value in the Arcane Environment field.

For example:

```dotenv
UNNAMED_TRACKING_APP_PORT=9000
```

would make the application available at:

```text
http://your-server:9000
```

## 6. Complete initial setup

On the first launch, open the application in your browser and follow the setup process.

The normal setup UI is preferred for creating the first user and configuring application settings.

If you configured provider credentials or OIDC values in Arcane, those deployment-owned values are available to the application during setup.

## Updating

When a new application image is available, use Arcane to pull the updated image and redeploy/recreate the stack.

Review the release or deployment documentation for the appropriate image tag before updating a production installation.

## Stopping the application

Use Arcane's stack controls to stop or remove the stack.

Removing the stack does **not** remove the named PostgreSQL volume or the bind-mounted application data unless you explicitly remove those Docker volumes/files.

## Next steps

- See [Environment Variables](../environment-variables.md) for configuration details.
- See [API Documentation](../development/api.md) for the automatically generated API documentation.
