# app/main.py
from fastapi import FastAPI

from src.api.routes import games, movies
from src.api.routes.utils import misc as utils_misc

app = FastAPI(
    title="My API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.include_router(games.router)
app.include_router(movies.router)
app.include_router(utils_misc.router)


@app.get("/health")
def health():
    return {"status": "ok"}
