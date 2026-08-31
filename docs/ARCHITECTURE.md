# Game Tracking Application Architecture Documentation

## 🎯 Overview
This application is designed as a modern, asynchronous API backend using FastAPI and SQLAlchemy (asyncio). It manages core game metadata, tracking player progress, and providing endpoints for a frontend client to consume. The entire system adheres to a Service Layer architectural pattern for clean separation of concerns.

## 🧱 Core Components & Responsibilities

### 1. Database Layer (`src/backend/database/*`)
*   **Purpose:** Defines the data schema (Models) and manages all interactions with the database engine (SQLAlchemy).
*   **Components:**
    *   `base.py`: Contains `Base` class, defining common metadata. It houses the crucial `transaction_scope` context manager, which ensures atomic database transactions (commit on success, rollback on failure).
    *   `models/game.py`, `developer.py`, `achievement.py`: Define the primary ORM models (`Game`, `Developer`, `Achievement`). These map Python classes to database tables and define relationships between them using SQLAlchemy's declarative system.
*   **Design Principle:** All data access must pass through a session manager derived from this layer.

### 2. Service Layer (`src/backend/services/api_service.py`)
*   **Purpose:** This is the **business logic heart** of the application. It contains all domain-specific rules, calculations, and workflows that are independent of HTTP requests.
*   **Responsibilities:**
    *   Translates raw API calls into complex database operations (e.g., fetching games requires calculating derived fields).
    *   Manages multi-step transactions that involve more than one simple CRUD operation (e.g., `run_poc` simulates a complex validation workflow).
    *   **Decoupling:** It completely hides the ORM/SQLAlchemy details from the API layer, making the API endpoints lightweight and focused only on request parsing and response formatting.

### 3. API Layer / Routing (`src/backend/main.py`)
*   **Purpose:** Acts as the public interface (the "Controller"). It handles HTTP requests, validates input data types, calls the appropriate method in the Service Layer, and formats the final HTTP response or exception.
*   **Workflow Example (`/api/v1/games/`):**
    1.  Receives `GET` request.
    2.  Calls `ApiService.get_all_games(session)`.
    3.  Handles exceptions raised by the Service Layer and converts them into standardized FastAPI HTTP exceptions (e.g., 404, 500).

## 🔄 Data Flow Summary (Example: Creating a Game)
1.  **Client Request:** Frontend sends `POST` request to `/api/v1/games/` with game data.
2.  **API Layer (`main.py`):** Receives the JSON body, validates structure, and calls `api_service.create_game(session, data)`.
3.  **Service Layer (`api_service.py`):** Executes business logic (e.g., ensuring unique folder names, setting default status). It obtains a session from the context manager provided by the database layer.
4.  **Database Layer (`base.py` $\rightarrow$ `models/game.py`):** The ORM model is instantiated and added to the transaction scope. The session executes the `INSERT` statement against the PostgreSQL database.

## 🚀 Next Steps & Improvements
*   **Unit Testing:** Implement comprehensive unit tests for all methods in `ApiService` to ensure business rules are maintained regardless of API changes.
*   **Error Handling:** Centralize custom exceptions within the Service Layer rather than relying solely on generic Python `Exception`.
*   **Validation:** Integrate Pydantic models directly into FastAPI endpoints to enforce data validation early.