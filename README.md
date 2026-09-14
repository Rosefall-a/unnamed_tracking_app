# Running the API

docker compose down -v
docker compose up -d --build
docker compose run --rm backend

# Backend checks
cd src/backend
mypy --config-file pyproject.toml src
pylint --rcfile=pyproject.toml src

# Frontend checks
cd /src/frontend
npm run lint
npm run format # if this fails run npm run format:fix
npm run typecheck

## Recommended VS Code extensions
- Ruff by charliermarsh

# Database updates

```bash
docker compose exec backend alembic -c alembic.ini revision --autogenerate -m "your changes here eg add playtime to game table"
```

## Central Docker image

The repository also publishes a central Docker image containing both the existing backend and frontend applications. The standalone backend and frontend images remain available and are still built by the existing Docker workflow.

The central image uses the same backend `requirements.txt`, the same Python 3.12/BlueMap runtime, and the same frontend `package.json` rather than maintaining duplicate dependency manifests.

### Build locally

From the repository root:

```bash
docker build -f Dockerfile.central -t unnamed-tracking-app-central .
```

### Run modes

Set `APP_MODE` to choose which application(s) the container starts:

- `both` (default): starts the backend on port `8000` and Vite on port `80`.
- `backend`: starts only the backend on port `8000`.
- `frontend`: starts only Vite on port `80`.

For the normal combined setup, publish both ports and provide the same environment variables required by the backend:

```bash
docker run --rm \
  --env-file .env \
  -p 5173:80 \
  -p 8000:8000 \
  unnamed-tracking-app-central
```

The frontend's `/api` requests are proxied by Vite to `BACKEND_URL`. For the central image, the default is `http://127.0.0.1:8000` because both processes share the same container. If the frontend is run separately with Docker Compose, set `BACKEND_URL=http://backend:8000` so the existing service-name networking continues to work.

To run only one side:

```bash
docker run --rm --env-file .env -e APP_MODE=backend -p 8000:8000 unnamed-tracking-app-central
docker run --rm --env-file .env -e APP_MODE=frontend -p 5173:80 unnamed-tracking-app-central
```

The central image is intended to be a convenient single-container deployment/development option. It does not replace the existing individual image workflow, and the central GitHub Action publishes it separately as the `-central` GHCR image.

## Security

This project is not currently hardened for direct public-internet exposure. Keep the API behind an appropriate network boundary and do not expose it directly to the public internet.
