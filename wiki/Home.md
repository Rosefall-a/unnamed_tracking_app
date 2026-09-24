# Unnamed Tracking — Wiki

Unnamed Tracking is a self-hosted media, game, library and save-tracking application.

This initial wiki is derived from the current `main` branch. It deliberately documents the implementation as it exists rather than treating older documentation or planned features as current behaviour.

## Start here

- [[Installation]] — development and production Compose deployments.
- [[Environment Variables]] — every application/deployment environment variable currently identified in the repository, including defaults and actual consumers.
- [[Architecture]] — backend, frontend, database, Docker and startup architecture.
- [[Authentication]] — local sessions, API keys, setup and OIDC/SSO.
- [[Integrations]] — metadata providers, deployment-wide credentials and precedence rules.
- [[Playnite Extension]] — how the companion Playnite extension connects and synchronizes.
- [[Operations]] — migrations, backups, startup diagnostics and production deployment.
- [[Development]] — local development, tests, linting and repository structure.
- [[Known Limitations]] — implementation/documentation gaps that should not be mistaken for supported guarantees.

## Source documentation

The repository already contains useful documentation:

- `docs/SETUP.md`
- `docs/OIDC.md`
- `docs/production-container.md`
- `docs/migrations.md`
- `devdocs/production-container.md`

The wiki is intended to be the operator-facing index and explanation layer; detailed implementation notes can remain in `docs/` and `devdocs/`.

## Important security note

The repository itself states that the application is not currently hardened for direct public-internet exposure. A reverse proxy/network boundary and HTTPS should be used for production deployments.

Never publish a real `.env`, API key, OIDC client secret, password or Fernet `SECRET_KEY`.
