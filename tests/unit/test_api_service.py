import httpx
from typing import Optional, List, Dict, Any

# Placeholder for the base API URL. This should ideally come from an environment variable.
BASE_URL = "http://localhost:8000" 

class APIServiceError(Exception):
    """Custom exception for handling API service errors."""
    pass

class ApiService:
    """
    Service class responsible for abstracting all interactions with the backend API.
    This layer makes unit testing easier by isolating HTTP calls from business logic.
    """

    def __init__(self, base_url: str = BASE_URL):
        self.client = httpx.Client(base_url=base_url)

    def get_health_check(self) -> bool:
        """Checks the basic connectivity and health of the API."""
        try:
            response = self.client.get("/health")
            if response.status_code == 200 and response.json().get("status") == "OK":
                return True
            else:
                raise APIServiceError(f"Health check failed: Status {response.status_code}")
        except httpx.ConnectError as e:
            print(f"Connection error during health check: Is the API running at {BASE_URL}? ({e})")
            return False

    # --- Game Operations ---

    def get_all_games(self) -> Optional[List[Dict[str, Any]]]:
        """Fetches a list of all games, returning parsed JSON data."""
        try:
            response = self.client.get("/api/v1/games/")
            response.raise_for_status() # Raises an exception for 4xx or 5xx status codes
            return response.json().get("games") # Assuming the API wraps games in a 'games' key
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                print(f"API Error: Resource not found at {e.request.url}")
                return None
            raise APIServiceError(f"HTTP error fetching games: {e.response.status_code}")
        except httpx.RequestError as e:
             raise APIServiceError(f"Connection error when fetching games: {e.__class__.__name__}")

    def create_game(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Creates a new game record via the API."""
        try:
            response = self.client.post("/api/v1/games/", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Specific handling for common errors like unique constraints
             if e.response.status_code == 409:
                 error = e.response.json().get("message", "Conflict")
                 raise APIServiceError(f"Creation failed due to conflict (e.g., folder location exists): {error}")
             raise APIServiceError(f"HTTP error creating game: {e.response.status_code}")
        except httpx.RequestError as e:
            raise APIServiceError(f"Connection error when creating game: {e.__class__.__name__}")

    # Add other CRUD operations (get_game, update_game, delete_game) here...


# -----------------------------------------------------------
# Unit Test Coverage for ApiService
# -----------------------------------------------------------
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import sessionmaker # Import necessary types to avoid direct dependency issues

@pytest.fixture
def api_service():
    """Fixture that provides a fresh instance of the API service."""
    return ApiService(base_url="http://localhost:8000")


# Mocking httpx client methods for isolated testing is complex, 
# so we will patch the entire class/method to simulate responses.

@patch("src.backend.api_service.httpx.Client")
def test_health_check_success(MockHttpClient):
    """Tests successful API health check."""
    mock_client_instance = MockHttpClient.return_value.__enter__.return_value
    # Simulate a successful GET response (200 OK)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "OK"}
    mock_client_instance.get.return_value = mock_response

    service = ApiService() # This will use the mocked client
    assert service.get_health_check() is True

@patch("src.backend.api_service.httpx.Client")
def test_health_check_failure(MockHttpClient):
    """Tests failure when API returns non-200 status."""
    mock_client_instance = MockHttpClient.return_value.__enter__.return_value
    # Simulate a failed GET response (403 Forbidden)
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {"error": "Forbidden"}
    mock_client_instance.get.return_value = mock_response

    service = ApiService()
    assert service.get_health_check() is False


@patch("src.backend.api_service.httpx.Client")
def test_create_game_success(MockHttpClient):
    """Tests successful game creation and status code handling."""
    mock_client_instance = MockHttpClient.return_value.__enter__.return_value
    # Simulate success response (201 Created)
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "new-game-uuid", "message": "Game created successfully"}
    mock_client_instance.post.return_value = mock_response

    service = ApiService()
    result = service.create_game({"title": "Test", "folder_location": "test"})
    assert result is not None
    assert "new-game-uuid" in str(result)


@patch("src.backend.api_service.httpx.Client")
def test_create_game_conflict(MockHttpClient):
    """Tests handling of unique constraint violations (409 Conflict)."""
    mock_client_instance = MockHttpClient.return_value.__enter__.return_value
    # Simulate conflict response (409 Conflict)
    mock_response = MagicMock()
    mock_response.status_code = 409
    mock_response.json.return_value = {"message": "Folder location already taken"}
    mock_client_instance.post.return_value = mock_response

    service = ApiService()
    with pytest.raises(APIServiceError) as excinfo:
        service.create_game({"title": "Test", "folder_location": "existing"})
    assert "Conflict" in str(excinfo.value)