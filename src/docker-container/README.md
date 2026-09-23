# Production container

This directory contains the production packaging for Unnamed Tracking. It is separate from the existing development frontend/backend images.

The image provides:
- one production image
- a compiled Vue frontend with no Vite development server
- Nginx as the public edge
- FastAPI behind Nginx
- an independent startup/status page
- database readiness and migrations
- a Docker Compose deployment example

Image name: ghcr.io/rosefall-a/unnamed_tracking_app:<tag>

The existing frontend and backend images remain available for development. The production package is an additional deployment target.

The startup page is served directly by Nginx before the backend is available. Its small static assets provide the UI; the entrypoint updates a small status JSON file and detail logs. Once FastAPI is healthy, Nginx reloads into the production configuration.

The startup UI polls asynchronously and uses no frontend framework. It is intended to remain lightweight and independent from the main Vue application.

TLS and certificate generation are deliberately not part of this initial implementation.

## Repository ownership

This production package is maintained in the Rosefall-a Unnamed Tracking repository. The development Docker images remain separate.

## Related repository changes in this PR

The PR also contains supporting CI/Compose adjustments outside this directory:
- the root Compose file includes the production app service while retaining the previous split frontend/backend development definitions as commented reference;
- frontend checks are path-scoped and avoid attempting to push formatting changes from forked pull requests;
- Ruff formatting is likewise prevented from attempting fork-branch pushes.

These changes are documented here because they are part of the actual PR, rather than implying that the production package alone is the entire diff.
