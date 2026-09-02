# app/main.py
from fastapi import FastAPI

from src.api.routes import games
from src.api.routes.utils.misc import router as misc_router

app = FastAPI(
    title="My API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.include_router(games.router)
app.include_router(misc_router)


@app.get("/health")
def health():
    return {"status": "ok"}
