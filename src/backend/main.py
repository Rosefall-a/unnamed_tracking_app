# app/main.py
from fastapi import FastAPI, HTTPException
import httpx
from typing import Dict, Any
from app.services.api_service import ApiService # Assuming the service file is structured here

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

@app.get("/api/v1/games/")
async def get_all_games_route():
    """Fetches a list of all registered games from the database."""
    try:
        # Use the dedicated service layer to handle connection and logic
        game_list = api_service.get_all_games() 
        if game_list is None:
            raise HTTPException(status_code=404, detail="No games found or API error.")
        return {"message": "Success", "games": game_list}
    except Exception as e:
         # Catch service layer errors (e.g., connection failure) and map them to HTTP exceptions
         raise HTTPException(status_code=500, detail=f"Internal server error fetching games: {str(e)}")

@app.post("/api/v1/games/")
async def create_game_route(game_data: Dict[str, Any]):
    """Creates a new game record in the system."""
    try:
        # Use the dedicated service layer for creation logic
        created_game = api_service.create_game(game_data)
        return {"message": "Game created successfully", "game_details": created_game}
    except Exception as e:
         raise HTTPException(status_code=400, detail=f"Failed to create game: {str(e)}")


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

