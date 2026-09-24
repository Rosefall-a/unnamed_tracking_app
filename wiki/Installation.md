# Installation

## Development stack

The root `compose.yaml` runs three logical services:

- PostgreSQL
- FastAPI backend
- Vue/Vite frontend

Copy `example.env` to `.env`, replace secrets, then run:

```bash
docker compose up --build
```

The frontend is exposed at `http://localhost:5173`. The frontend Vite proxy sends `/api` to the Docker Compose `backend:8000` service, so browser API requests remain same-origin.

The backend applies Alembic migrations before starting Uvicorn.

## First-run setup

New installations normally create the first administrator through the web setup flow rather than through environment variables.

The frontend checks `/api/setup/status`. With an empty database it opens `/setup`; once a user exists, normal authentication is used.

Legacy `PRIMARY_USER_*` variables remain supported for deployments that intentionally seed the original account automatically.

## Production image

The production deployment is under `src/docker-container/`.

The recommended Compose file is:

```text
src/docker-container/compose.yaml
```

It runs the published GHCR image, PostgreSQL and Nginx-backed startup/production serving.

The normal production sequence is:

1. Nginx serves the independent startup page.
2. Required configuration is checked.
3. PostgreSQL readiness is checked.
4. Alembic migrations are applied.
5. FastAPI starts on localhost.
6. `/health` is checked.
7. Nginx validates the ready configuration.
8. Nginx switches to the compiled Vue frontend/API proxy.
9. PID 1 continues monitoring the backend.

## Production environment

The production example is `src/docker-container/.env.example`. It is intentionally smaller than the development `example.env`.

Required production secrets include:

- PostgreSQL password
- `SECRET_KEY`
- primary-user password when legacy bootstrap is used

Set `AUTH_COOKIE_SECURE=true` when the public endpoint is HTTPS.

## Volumes

Both example Compose deployments persist PostgreSQL data. The application also uses `./data:/data` for application filesystem storage.

## Do not expose PostgreSQL publicly

The database service does not need a host port mapping in the supplied Compose examples. Keep it on the private Compose network.
