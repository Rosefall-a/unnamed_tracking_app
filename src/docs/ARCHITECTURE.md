# Project Architecture Documentation

## 🏗️ Overview
This project implements an application for tracking games, developers, and achievements across multiple titles. It follows a decoupled microservice-like structure where the Frontend UI communicates exclusively with the Backend API via REST endpoints. Both services are containerized using Docker Compose.

**Technology Stack:**
*   **Backend API:** Python 3.10+, FastAPI, SQLAlchemy 2.0 (Async/Sync Mix), PostgreSQL (via Alembic migrations).
*   **Frontend UI:** Vue 3, Vite, TypeScript, Pinia (State Management).

---

## ⚙️ Backend Architecture (`src/backend/`)

The backend is responsible for all business logic, data persistence, and API exposure. It follows a layered architecture:

1.  **Models Layer (`database/models/*.py`):** Contains SQLAlchemy ORM models defining the schema (e.g., `Game`, `Developer`, `Achievement`). This layer interacts directly with the database session via declarative base classes.
2.  **Database Layer (`database/session.py`):** Manages the database connection and session handling, ensuring transactional integrity.
3.  **Service Layer (`services/*.py` - *Planned*):** (Conceptual) Business logic should ideally live here to decouple models from API endpoints. This layer validates data and coordinates multiple model operations before committing them.
4.  **API/Endpoint Layer (`api/v1/*`):** Contains FastAPI Routers. These handle HTTP requests, validate incoming Pydantic payloads, call the necessary services, and return structured JSON responses.

### Key Data Models & Relationships:
*   **Game:** Core entity representing a game title (e.g., *Elden Ring*). Stores metadata like folder location, release date, status, and user ratings/playtime.
*   **Developer:** Represents the creator of a game (e.g., *FromSoftware*). One developer can create multiple games.
*   **Achievement:** Defines milestones for a game. Many-to-One relationship with `Game`.

### Data Flow Summary (Client $\rightarrow$ Server):
1.  User interaction triggers an HTTP request to the API Gateway endpoint (`/api/v1/...`).
2.  FastAPI receives the request, validates it against Pydantic schemas, and passes control to the relevant router function.
3.  The router calls a service or directly interacts with models (in early stages).
4.  SQLAlchemy handles ORM mapping, database interaction, and transaction commitment.

## 🌐 Frontend Architecture (`src/frontend/`)

The frontend is responsible for providing a rich, interactive user interface built with Vue 3 and Vite. It consumes the API exposed by the Backend API Container (`unnamed_tracking_app-api`). The architecture follows modern SPA principles:

*   **Structure:** Components are organized into reusable units (e.g., `GameCard.vue`, `Header.vue`) within a modular directory structure under `src/components`.
*   **State Management:** Pinia (recommended) will be used to manage global state, such as the list of games, user profile data, and application settings. This keeps component logic clean and predictable.
*   **Data Fetching:** All communication with the backend is handled by a dedicated service layer (`src/services/*`). This decouples UI components from network requests, making them easily testable.
    *   Example: `gamesService.ts` encapsulates all API calls to `/api/v1/games`.
*   **Routing:** Vue Router handles navigation between major views (e.g., Game List, Game Detail, Add New Game).

**Data Flow Summary (Client $\rightarrow$ Server):**
1.  User interacts with a Component in the UI.
2.  The component calls a function in the relevant Service Layer (`gamesService`).
3.  The Service Layer constructs an HTTP request and uses `axios` or `fetch` to call the FastAPI endpoint.
4.  The backend handles validation, business logic, database interaction, and returns structured JSON data.

## 🚀 Next Steps & Improvements
*   **Unit Testing:** Implement comprehensive unit tests for all methods in `ApiService` to ensure business rules are maintained regardless of API changes.
*   **Error Handling:** Centralize custom exceptions within the Service Layer rather than relying solely on generic Python `Exception`.
*   **Validation:** Integrate Pydantic models directly into FastAPI endpoints to enforce data validation early.

## 🚧 Implementation Notes
*   **Consistency:** All data models used on the frontend should mirror the structure defined in the API response schemas (Pydantic/TypeScript).
*   **Documentation:** New features or complex endpoints MUST update both this document and the corresponding `README.md`.