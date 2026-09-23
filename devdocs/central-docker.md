# Central Docker architecture

The central image deliberately reuses the repository's backend dependency manifest and frontend package manifest rather than maintaining a second application implementation.

## Build layout

`src/central/Dockerfile` uses a Node build/runtime layer and the existing Python runtime. It copies `src/backend/src` into `/app/src` so the normal `uvicorn src.main:app` import layout is retained.

`entrypoint.sh` owns process selection. In `both` mode it starts both processes and exits if either process terminates, preventing a half-alive container.

## Backend URL resolution

The Vite configuration already resolves the proxy target as:

1. explicit `BACKEND_URL`;
2. localhost in `APP_MODE=both`;
3. `backend:8000` for separate frontend/backend containers.

Do not hard-code `backend:8000` into application code. This is important because a combined container has no Docker DNS service named `backend`.

## Adding a central mode

If a new mode is needed, update the case statement in `entrypoint.sh`, document its ports and process lifecycle here, and add a compose example. Avoid adding a supervisor unless process requirements become materially more complex.

## Docker CI

The existing Docker checks should remain unchanged. The central image can have a dedicated build check, but existing backend/frontend checks must not be removed or weakened.
