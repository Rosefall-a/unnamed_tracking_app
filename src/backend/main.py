# app/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
from uuid import UUID
from pydantic import BaseModel

from app.services.api_service import ApiService

api_service = ApiService() 

app = FastAPI(
    title="Game Tracking API",
    description="Core API for managing and tracking games.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Catch-all for API 404s so FastAPI never returns HTML to fetch()
@app.exception_handler(404)
async def api_404_handler(request: Request, exc: Exception):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=404,
            content={"detail": f"API endpoint '{request.url.path}' not found."}
        )
    return JSONResponse(status_code=404, content={"detail": "Not found"})

# --- Models ---
class NotePayload(BaseModel):
    content: str

# --- Routes ---

@app.get("/health")
def health():
    return {"status": "ok"}

# Game Routes (Matching frontend /api/games/ path)
@app.get("/api/games/{game_uuid}")
async def get_single_game_route(game_uuid: UUID):
    try:
        game = api_service.get_game_by_id(game_uuid) 
        if not game:
            raise HTTPException(status_code=404, detail=f"Game with UUID {game_uuid} not found.")
        # Return raw game object directly to match frontend expectations
        return game
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.put("/api/games/{game_uuid}")
async def update_game_route(game_uuid: UUID, update_data: Dict[str, Any]):
    try:
        updated_game = api_service.update_game(game_uuid, update_data)
        return updated_game
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update game: {str(e)}")

@app.delete("/api/games/{game_uuid}")
async def delete_game_route(game_uuid: UUID):
    try:
        success = api_service.delete_game(game_uuid) 
        if not success:
            raise HTTPException(status_code=404, detail=f"Game with UUID {game_uuid} not found.")
        return {"message": "Game deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- Notes Routes (Required by GameDetail.vue) ---

@app.get("/api/games/{game_uuid}/notes", response_model=List[str])
async def list_game_notes_route(game_uuid: UUID):
    try:
        if hasattr(api_service, "list_notes"):
            return api_service.list_notes(game_uuid)
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing notes: {str(e)}")

@app.get("/api/games/{game_uuid}/notes/{note_name}")
async def fetch_game_note_route(game_uuid: UUID, note_name: str):
    try:
        if hasattr(api_service, "get_note"):
            content = api_service.get_note(game_uuid, note_name)
            return content  # Returns string/markdown
        return f"# {note_name}\nSample content"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching note: {str(e)}")

@app.post("/api/games/{game_uuid}/notes/{note_name}")
async def save_game_note_route(game_uuid: UUID, note_name: str, payload: NotePayload):
    try:
        if hasattr(api_service, "save_note"):
            api_service.save_note(game_uuid, note_name, payload.content)
        return {"message": "Note saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving note: {str(e)}")

@app.delete("/api/games/{game_uuid}/notes/{note_name}")
async def delete_game_note_route(game_uuid: UUID, note_name: str):
    try:
        if hasattr(api_service, "delete_note"):
            api_service.delete_note(game_uuid, note_name)
        return {"message": "Note deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting note: {str(e)}")

@app.get("/api/poc-test")
def run_poc():
    success, message = api_service.run_poc()
    return {"success": success, "message": message}