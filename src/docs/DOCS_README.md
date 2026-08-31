# Project Documentation

This directory serves as the central repository for all technical documentation, architectural overviews, and guides related to the Game Tracking API.

## 📚 Core Modules Overview

*   **[Architecture Diagram](link/to/diagram):** (Future addition) High-level overview of services interaction.
*   **[API Endpoints Reference](/docs/api_endpoints.md):** Detailed list of all available REST endpoints, including request bodies and expected responses.
*   **[Database Schema Migration Guide](/docs/migration_guide.md):** Guidelines for using Alembic to manage schema changes safely.

## 💻 Setup & Development Environment

*(See `README.md` in the project root for initial setup steps.)*

### Unit Testing Protocol
All services and business logic must be covered by unit tests located in `tests/unit/`. The API service layer should be tested using mocks to ensure no external network calls are required during testing.

## 🗄️ Data Integrity & Disaster Recovery
*(Refer to the root README for critical backup instructions.)*