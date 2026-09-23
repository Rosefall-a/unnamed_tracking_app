# Central Docker image

The central image packages the existing frontend and backend runtimes into one container.

## Modes

`APP_MODE=both` starts the API on port 8000 and the Vite frontend on port 80.
`APP_MODE=backend` starts only the API. `APP_MODE=frontend` starts only the frontend.

The frontend proxy defaults to `http://127.0.0.1:8000` in the combined container. Set `BACKEND_URL` when the frontend needs to reach a separately deployed backend.

The image still expects PostgreSQL through `DATABASE_URL`; the included compose example provides PostgreSQL separately.

## Configuration

Copy `src/central/example.env` and replace all secrets. Do not commit production `.env` files.
