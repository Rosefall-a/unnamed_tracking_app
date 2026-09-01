# app/main.py
from fastapi import FastAPI

from src.api.routes import games

app = FastAPI(
    title="My API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.include_router(games.router)


@app.get("/health")
def health():
    return {"status": "ok"}
