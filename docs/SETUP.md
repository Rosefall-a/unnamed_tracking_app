# Self-hosted setup

This branch uses a first-run web setup for the administrator. Provider API keys and deployment-wide OIDC credentials can be entered from **Settings → Server Integrations** after the first administrator is created.

## 1. Example `.env`

Copy this to `.env` at the repository root. Do not commit your real `.env`.

```dotenv
POSTGRES_USER=archive
POSTGRES_PASSWORD=change-this-database-password
POSTGRES_DB=archive

# Required: used for Fernet encryption and signing the server-side session.
# Generate one with:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SECRET_KEY=replace-with-a-generated-fernet-key

# Local HTTP development only. Set true when the app is served over HTTPS.
AUTH_COOKIE_SECURE=false

# No provider API keys are required here for a new install.
# Configure deployment-wide provider credentials from Settings instead.

# Optional legacy first-admin bootstrap. Leave unset for the normal web setup.
# PRIMARY_USER_USERNAME=admin
# PRIMARY_USER_EMAIL=admin@example.com
# PRIMARY_USER_PASSWORD=Change-this-during-setup

# Optional OIDC environment fallback. Prefer Settings → Server Integrations.
# OIDC_ISSUER_URL=https://login.example.com/realms/archive
# OIDC_CLIENT_ID=archive
# OIDC_CLIENT_SECRET=replace-me
# OIDC_REDIRECT_URI=http://localhost:5173/api/auth/oidc/callback
# OIDC_SCOPES=openid profile email
```

## 2. Example Docker Compose

The repository's `compose.yaml` is the recommended Compose configuration. The backend Dockerfile is named `dockerfile` (lowercase), and Compose references it explicitly so the setup works on case-sensitive Linux hosts.

```yaml
services:
  db:
    image: postgres:18
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build:
      context: ./src/backend
      dockerfile: dockerfile
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./src/frontend
    restart: unless-stopped
    env_file: .env
    depends_on:
      - backend
    ports:
      - "5173:80"

volumes:
  pgdata:
```

The frontend's Vite proxy sends `/api` requests to the `backend` service, so the browser uses one origin. That also means the OIDC callback should normally point at the browser-facing frontend URL, for example `http://localhost:5173/api/auth/oidc/callback`.

## 3. Start the application

```bash
docker compose up --build
```

The backend applies pending Alembic migrations with `alembic upgrade heads` before starting Uvicorn. This is intentional: a fresh PostgreSQL volume has no application tables, so the first-run setup endpoint cannot work until the schema exists. The migration command targets **all migration heads**, avoiding the earlier `upgrade head` ambiguity while still applying every branch of a legitimate migration graph.

Open `http://localhost:5173`. The frontend checks `/api/setup/status` before checking authentication. On a database with no users it sends you to `/setup`, where you create the first administrator.

If the backend is stopped, the frontend stays on the setup/unavailable screen instead of incorrectly sending a fresh installation to `/login`.

## 4. Configure provider credentials

After signing in as an administrator, open **Settings → Server Integrations**. Deployment-wide credentials are stored encrypted in PostgreSQL. The browser never receives the saved secret values; password/API-key fields show that a value exists and require a new value to replace it.

Per-user credentials already available in the Metadata/API settings continue to take precedence over deployment-wide fallbacks.

## 5. Configure OIDC / SSO

In **Settings → Server Integrations → OpenID Connect / SSO**, enter:

- **Issuer URL** — the OIDC issuer, such as `https://login.example.com/realms/archive`.
- **Client ID** — the client/application ID registered with your identity provider.
- **Client secret** — the confidential client secret. It stays on the backend and is encrypted at rest.
- **Scopes** — normally `openid profile email`.
- **Redirect URI** — the exact browser-facing callback URL. With the example Compose setup this is `http://localhost:5173/api/auth/oidc/callback`.

Register that exact redirect URI with the identity provider. After saving, the login page displays **Continue with SSO**. The UI starts the redirect and displays friendly error messages, while the backend performs the authorization-code exchange and creates the application's local session.

The OIDC flow requires a verified email claim. Existing users are matched by OIDC subject first and verified email second; new OIDC users are created as non-admin users.

## 6. Is `SECRET_KEY` required?

**Yes.** `SECRET_KEY` remains the one important application secret that should stay in the environment rather than the Settings UI.

This application uses it for two security-critical purposes:

1. FastAPI/Starlette's server-side session middleware signs the session data used by the OAuth/OIDC flow.
2. The application's Fernet encryption layer uses it to encrypt recoverable secrets such as provider credentials and PSN tokens.

It must be a valid Fernet key and must remain stable across restarts. Generate it with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Do **not** regenerate it on every container start: changing it makes previously encrypted values unreadable and invalidates signed sessions.

## Production notes

- Put the application behind HTTPS and set `AUTH_COOKIE_SECURE=true`.
- Keep PostgreSQL private; it does not need to be exposed to the public internet.
- Keep `.env` out of source control.
- Use a long, randomly generated Fernet `SECRET_KEY`.
- Prefer the Settings UI for provider and OIDC credentials so they are encrypted in the database instead of copied into deployment files.
- The environment variables for provider/OIDC credentials remain as backwards-compatible fallbacks for existing deployments.
