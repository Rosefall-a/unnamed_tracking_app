# API Documentation

## Endpoints
- **GET /users**: Retrieve a list of users.
- **POST /users**: Create a new user.
- **GET /users/{id}**: Retrieve a single user by ID.
- **PUT /users/{id}**: Update a user by ID.
- **DELETE /users/{id}**: Delete a user by ID.

## Authentication
- Bearer token authentication is required for all endpoints except `/users`.
- Token can be obtained via the `/auth/login` endpoint.

## Error Handling
- All responses include a status code and a message.
- 401 Unauthorized: Invalid or expired token.
- 403 Forbidden: Access denied.
- 404 Not Found: Resource not found.
- 500 Internal Server Error: An error occurred on the server.