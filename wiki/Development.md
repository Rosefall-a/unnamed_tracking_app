# Development

## Backend

From the repository root:

```bash
cd src/backend
mypy --config-file pyproject.toml src
pylint --rcfile=pyproject.toml src
```

Backend tests normally run against the running Compose PostgreSQL service:

```bash
docker compose exec -e PYTHONPATH=/app backend python -m pytest tests -q
```

## Frontend

From `src/frontend`:

```bash
npm ci
npm run lint
npm run format
npm run typecheck
npm run test
```

The Vite development container uses polling because Docker Desktop filesystem events can otherwise prevent HMR from firing reliably.

## Docker

There are intentionally separate development images and an assembled production image.

Do not assume the production image replaces the development backend/frontend workflows.

## Documentation sources

### Operator-facing

- `docs/SETUP.md`
- `docs/OIDC.md`
- `docs/production-container.md`
- `docs/migrations.md`

### Developer-facing

- `devdocs/production-container.md`

### Historical/design notes

- `Notes/BUILD-1-FOUNDATIONS.md`
- `Notes/BUILD-2-BACKEND.md`
- `Notes/DESIGN.md`

The Notes directory should be treated as design/build history rather than a guaranteed description of the current implementation.

## CI behaviour

Backend/frontend/Docker checks are configured to run on pushes and on pull requests when the pull request is ready for review rather than draft. Some workflows retain write permissions because they can auto-format same-repository branches.

The production-container workflow currently builds the assembled image on pull requests but only publishes it on non-PR runs.

## Code organisation

Backend code is grouped into:

- API routes/schemas
- core authentication/configuration/crypto/integration helpers
- database models/session/migrations
- feature modules for jobs, backup, trash, metadata and world-map functionality

The frontend is split into services, components, composables, stores and views.

The Playnite extension is maintained separately and should not be treated as part of the web frontend build.
