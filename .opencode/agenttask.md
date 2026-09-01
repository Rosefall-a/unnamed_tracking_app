Status markers:

TODO — not started

IN‑PROGRESS — currently being worked on

DONE — completed

Phase 1 — Repository Understanding
1.1 Review Repository Structure — TODO
Backend: FastAPI app (src/backend/src), database models (src/backend/database), services (src/backend/services), Alembic migrations (alembic.ini), dependencies (pyproject.toml, requirements.txt).
Frontend: Vite project (src/frontend), components (src/frontend/src), public assets (src/frontend/public), configs (tsconfig.json, vite.config.ts).
Docker: compose.yaml, example-docker-compose.yaml.
Scripts: generate-the-.env.-please.sh.
Documentation: BUILD-1-FOUNDATIONS.md, BUILD-2-BACKEND.md, DESIGN.md, APIS.md, Data.md.

1.2 Identify Missing & Partial Components — TODO
Backend missing: auth, websockets, error handling.
Frontend missing: auth flows, forms, responsive design.
Database missing: indexing, constraints.
Docker missing: CI/CD, production configs, optimized Dockerfiles.
Tests missing: backend unit tests, integration tests, E2E tests.
Docs missing: API docs, user guides.

Phase 2 — Core Development
2.1 CI/CD Pipeline Setup — TODO
Create GitHub Actions workflow for CI.

Create GitHub Actions workflow for CD.
Agent: devops

2.2 Production Docker Setup — TODO
Update compose.yaml for production (backend, frontend, database).

Create backend Dockerfile (FastAPI + uvicorn).

Create frontend Dockerfile (Vite build + nginx).

Add .dockerignore files.
Agent: devops

2.3 Backend Authentication & Authorization — TODO
Implement JWT auth.

Add role-based authorization.
Agent: backend

2.4 Frontend Authentication & Authorization — TODO
Integrate Redux Toolkit.

Implement auth flows (Supabase/Firebase).
Agent: frontend

Phase 3 — Database & API
3.1 Database Indexing & Constraints — TODO
Add constraints, validations, indexes.
Agent: backend

3.2 API Documentation — TODO
Add Swagger/OpenAPI docs.
Agent: docs

3.3 Real-Time Features (Optional) — TODO
Implement websockets.

Add frontend websocket listeners.
Agent: backend + frontend

Phase 4 — Testing & QA
4.1 Backend Unit Tests — TODO
Write pytest/unittest coverage.
Agent: backend

4.2 Integration & E2E Tests — TODO
Jest/Cypress tests.

GitHub Actions E2E pipeline.
Agent: frontend + devops

4.3 Performance Refactoring — TODO
Profile backend.

Refactor slow components.
Agent: general + backend

Phase 5 — Deployment & Monitoring
5.1 Deployment (Docker) — TODO
Build backend Docker image.

Build frontend Docker image.

Deploy via Docker (AWS ECS, Heroku container registry, or similar).
Agent: devops

5.2 Monitoring & Logging — TODO
Add Prometheus/Grafana.

Add structured logging.
Agent: devops + backend

Agent Instructions
After completing each task:

Mark the task as DONE.

Add a short summary under the task.

Commit changes to a branch named:

Code
agent/<task-id>
Push ONLY that branch.

Move to the next task.