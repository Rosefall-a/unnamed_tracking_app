import pytest
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

# Import the service to be tested
from app.services.api_service import ApiService 

@pytest.fixture(scope="module")
def api_service():
    """Fixture providing a fresh instance of the API Service."""
    return ApiService()

@pytest.fixture(scope="function")
def mock_session():
    """Fixture to provide a mocked asynchronous session object for testing DB interactions."""
    mock = AsyncMock(spec=AsyncSession)
    # Setup basic mocking for common methods used in the service layer (e.g., execute, scalars, etc.)
    return mock

@pytest.mark.asyncio
async def test_get_all_games_success(api_service: ApiService, mock_session: AsyncMock):
    """Tests successful retrieval of all games."""
    # Arrange: Mock the return value for a successful call
    mock_games = [MagicMock()] * 3 # Simulate 3 game objects
    mock_session.scalars.return_value.all.return_value = mock_games

    # Act
    result = await api_service.get_all_games(mock_session)

    # Assert
    assert result == mock_games
    mock_session.scalars.all.assert_called_once()

@pytest.mark.asyncio
async def test_create_game_success(api_service: ApiService, mock_session: AsyncMock):
    """Tests successful creation of a new game."""
    # Arrange: Mock the return value for the created object
    mock_new_game = MagicMock()

    # Act
    result = await api_service.create_game(mock_session, {"title": "New Test Game", "folder_location": "test"})

    # Assert
    assert result is not None # Assuming service layer returns the created object
    mock_session.add.assert_called() # Check that the session was used to add data

@pytest.mark.asyncio
async def test_run_poc_success(api_service: ApiService, mock_session: AsyncMock):
    """Tests a successful execution of the Proof-of-Concept workflow."""
    # Arrange
    mock_session.begin.return_value = AsyncMock() # Mocking transaction start

    # Act
    result = await api_service.run_poc(mock_session)

    # Assert
    assert result[0] is True
    assert "successfully" in result[1]
