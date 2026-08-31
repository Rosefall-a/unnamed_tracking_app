# app/main.py
from fastapi import FastAPI

from app.api.routes import games

app = FastAPI(title="My API")

app.include_router(games.router)


@app.get("/health")
def health():
    return {"status": "ok"}