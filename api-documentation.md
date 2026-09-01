# API Documentation
## Introduction
This document outlines the API endpoints available for the backend service.
## Endpoints
### GET /api/v1/users
- **Description**: Retrieve a list of users.
- **Parameters**: None
- **Response**:
  - **Status Code**: 200
  - **Content-Type**: application/json
  - **Body**:
    ```json
    {
      "users": [
        {"id": 1, "name": "John Doe", "email": "john.doe@example.com"},
        {"id": 2, "name": "Jane Smith", "email": "jane.smith@example.com"}
      ]
    }
    ```

### POST /api/v1/users
- **Description**: Create a new user.
- **Parameters**:
  - `name` (string): The name of the user
  - `email` (string): The email address of the user
- **Response**:
  - **Status Code**: 201
  - **Content-Type**: application/json
  - **Body**:
    ```json
    {
      "id": 3,
      "name": "Jane Smith",
      "email": "jane.smith@example.com"
    }
    ```
