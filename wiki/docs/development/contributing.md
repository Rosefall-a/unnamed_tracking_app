# Contributing

## Development layout

Backend development happens under `src/backend`; frontend development happens under `src/frontend`.

Keep backend-only logic in the backend and frontend-only behavior in the frontend. Configuration rules belong in the backend configuration registry rather than being duplicated in Vue components.

## Backend checks

The backend CI runs its checks from `src/backend`.

The normal checks include:

- pytest
- mypy
- pylint

The backend uses Python 3.12 in CI.

When adding backend functionality, update or add tests with the change and keep type-checking and linting clean.

## Frontend checks

Frontend changes should pass the repository's frontend linting and build checks.

When changing shared frontend types, services, or list-loading behavior, check all media/library views that consume the affected service rather than fixing only the first view that exposes the error.

## Database changes

Use Alembic migrations for schema changes.

- Add a new migration rather than editing a migration that has already shipped.
- Keep one migration head.
- Test migrations against a fresh database and an existing database where practical.
- Do not use destructive database recreation as a normal development workflow.

## Configuration changes

For a new environment variable:

1. Add it to the backend configuration registry.
2. Decide whether it is deployment-owned (`ENV`), application-owned (`SETUP`), or supports both.
3. Add validation/dependencies where needed.
4. Add a safe example to `example.env`.
5. Document it on the [Environment Variables](../setup/environment-variables.md) page.
6. Add focused tests.

Do not add real credentials to `example.env`.

## Pull requests

Keep pull requests focused on one change where practical.

For bug fixes, include the related GitHub issue reference in the pull request so the issue can be automatically closed when the PR is merged.

Document user-facing behavior changes in the wiki when they affect setup, configuration, deployment, or normal application usage.
