# Central Docker architecture

The central image reuses the existing backend dependency manifest and frontend package manifest.

vite.config.ts resolves the proxy target in this order:

1. BACKEND_URL when explicitly supplied.
2. localhost:8000 when APP_MODE=both.
3. DEFAULT_BACKEND_URL from the image, which is backend:8000.
4. backend:8000 as the code-level fallback when no image default exists.

The Dockerfile sets DEFAULT_BACKEND_URL rather than hard-coding the combined-container address. This keeps backend:8000 as the global split deployment default while allowing combined mode to select localhost.

entrypoint.sh owns process selection. In both mode both processes are started and the container exits if either process stops.

Do not introduce a supervisor unless process requirements materially change.
