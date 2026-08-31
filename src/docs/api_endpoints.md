# Game Tracking API Endpoints Reference

This document details every available RESTful endpoint provided by the FastAPI backend. All endpoints are versioned under `/api/v1/`.

---

## 🌐 General Health Check
### `GET /health`
*   **Description:** Checks basic connectivity to the API server.
*   **Authentication:** None required.
*   **Success Response (200 OK):**
    ```json
    {
      "status": "ok"
    }
    ```

## 🎮 Game Management Endpoints (`/api/v1/games/`)
### `GET /api/v1/games/`
*   **Description:** Retrieves a list of all games currently tracked in the system. This is the primary endpoint for populating the dashboard.
*   **Request Body:** None.
*   **Success Response (200 OK):** Returns an object containing the array of game objects under the `games` key.
    ```json
    {
      "message": "Success",
      "games": [
        { 
          "id": "string_uuid", 
          "title": "Game Title", 
          "description": "The game's description.", 
          "status": "WISHLIST", 
          "playtime_seconds": 1200,
          "folder_location": "/path/to/game"
        }
      ]
    }
    ```
*   **Failure Response (404 Not Found):** If no games are found or the endpoint is unreachable.

### `POST /api/v1/games/`
*   **Description:** Creates a new game entry in the tracking system, which also creates corresponding folders and database records.
*   **Authentication:** Required (Details to be added).
*   **Request Body:**
    ```json
    {
      "title": "New Awesome Game",
      "description": "A wonderful new title.",
      "status": "BACKLOG",
      "folder_location": "/path/for/new/game" 
    }
    ```
*   **Success Response (201 Created):** Returns details of the newly created game object.
*   **Failure Response (409 Conflict):** Triggered if a `folder_location` already exists in the system, preventing data corruption.

## ✅ API Testing Endpoint
### `GET /api/poc-test`
*   **Description:** Runs a Proof-of-Concept sequence to verify that both the health check and the main `/games` listing endpoint are fully reachable and functional at runtime. Useful for automated deployment checks.
*   **Request Body:** None.

---
### 💡 Developer Notes
1.  All API operations rely on the `ApiService` service layer (`src/backend/api_service.py`) to handle connection pooling, retries, and error mapping before reaching FastAPI's router functions.
2.  Remember to add proper security checks (like JWT authentication) to all routes in `/api/v1/`.