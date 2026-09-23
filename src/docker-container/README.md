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

Existing frontend and backend images and their CI workflow are not replaced by this package.

The startup page is served directly by Nginx before the backend is available. Its small static assets provide the UI; the entrypoint only updates a tiny status JSON file and detail logs. Once FastAPI is healthy, Nginx reloads into the production configuration.

TLS and certificate generation are deliberately not part of this initial implementation.

## Repository ownership

This production package is maintained in the Rosefall-a Unnamed Tracking repository. The development Docker images remain separate and unchanged.
