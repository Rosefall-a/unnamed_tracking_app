# Central Docker image

The central image packages the existing frontend and backend runtimes into one container while PostgreSQL remains a separate service.

## Modes

APP_MODE=both starts the API on port 8000 and the frontend on port 80. The frontend defaults to the backend at 127.0.0.1:8000.

APP_MODE=backend starts only the API.

APP_MODE=frontend starts only the frontend. Its default backend target is backend:8000.

BACKEND_URL always overrides the calculated target.

The Docker image defines backend:8000 as the global split-deployment default. The frontend configuration changes that default to localhost only when APP_MODE=both.

## Compose examples

Build from the repository root:

docker build -f src/central/Dockerfile -t unnamed-tracking-app-central:local .

Combined deployment:

docker compose -f src/central/docker-compose.yaml up --build

Split deployment:

docker compose -f src/central/docker-compose.separate.yaml up --build

## Validation

Test all three APP_MODE values. For both mode, verify browser requests reach the backend through localhost. For frontend mode, verify requests reach backend:8000 or the explicit BACKEND_URL. For backend mode, verify the API is reachable directly. Also test a custom BACKEND_URL.

The existing separate backend/frontend deployment remains a supported deployment shape.
