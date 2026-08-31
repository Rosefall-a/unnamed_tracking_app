# app/main.py
from fastapi import FastAPI, HTTPException
import httpx
from typing import Dict, Any
from app.services.api_service import ApiService # Assuming the service file is structured here
from uuid import UUID, uuid4

# Initialize the API Service globally or in a startup event to manage connections efficiently
api_service = ApiService() 

app = FastAPI(
    title="Game Tracking API",
    description="Core API for managing and tracking games.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# --- Routes ---

@app.get("/health")
def health():
    """Basic endpoint to check API availability."""
    return {"status": "ok"}

@app.get("/api/v1/games/{game_uuid}")
async def get_single_game_route(game_uuid: UUID):
    """Retrieves a single game record by its unique identifier (UUID)."""
    try:
        # Check if the game exists and fetch details using service layer
        game = api_service.get_game_by_id(game_uuid) 
        if not game:
            raise HTTPException(status_code=404, detail=f"Game with UUID {game_uuid} not found.")
        return {"message": "Success", "game": game}
    except Exception as e:
         # Catch service layer errors and map them to HTTP exceptions
        raise HTTPException(status_code=500, detail=f"Internal server error fetching game details: {str(e)}")

@app.put("/api/v1/games/{game_uuid}/") # Using PUT for full replacement update
async def update_game_route(game_uuid: UUID, update_data: Dict[str, Any]):
    """Updates an existing game record using the provided data."""
    try:
        # The service layer handles validation and merging of new data.
        updated_game = api_service.update_game(game_uuid, update_data)
        return {"message": "Game updated successfully", "game_details": updated_game}
    except Exception as e:
         raise HTTPException(status_code=400, detail=f"Failed to update game: {str(e)}")

@app.delete("/api/v1/games/{game_uuid}")
async def delete_game_route(game_uuid: UUID):
    """Deletes a game record and related data (like achievements)."""
    try:
        # The service layer must handle cascading deletes carefully
        success = api_service.delete_game(game_uuid) 
        if not success:
            raise HTTPException(status_code=404, detail=f"Game with UUID {game_uuid} not found or could not be deleted.")
        return {"message": "Game deleted successfully"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Internal server error deleting game: {str(e)}")


@app.get("/api/poc-test")
def run_poc():
    """
    Runs a comprehensive Proof-of-Concept test sequence against core endpoints 
    (/health and /games/). Returns structured results of the connectivity check.
    """
    success, message = api_service.run_poc()
    return {"success": success, "message": message}

# Include routers/routes here when they are defined in dedicated files
# app.include_router(games.router) # This line is kept commented until 'app.api.routes' exists

