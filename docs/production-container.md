# Production container

The production image is a separate deployment target from the development frontend/backend images and is intended for deployment from the Rosefall-a Unnamed Tracking repository.

## User guide

Use src/docker-container/compose.yaml as the starting point for a production Compose deployment. Set a strong SECRET_KEY and primary-user password.

The published image is ghcr.io/rosefall-a/unnamed_tracking_app:<tag>. The container exposes one public HTTP port. PostgreSQL is a separate service with a persistent volume.

On first access, Nginx immediately serves the production startup page. It reports database, migration, backend, and frontend state. When the application is ready, Nginx reloads and begins serving the built Vue application at /.

## Startup and failure behaviour

The startup page does not require FastAPI, Vue, Node, or PostgreSQL to render. Nginx serves it directly. If startup fails, the status page remains available and exposes the current phase and startup details.

The page is intentionally a small static HTML/CSS/JavaScript application. It polls a small JSON status document once per second and uses no frontend framework.

## Development versus production

The existing development Compose file and existing frontend/backend Docker workflow are intentionally unchanged. Development continues to use Vite and the existing split images. The production container builds the frontend with npm run build and serves the resulting static files through Nginx.

## TLS

TLS certificate handling is intentionally not included yet. Future TLS work can be added at the Nginx layer without changing the application process model.
