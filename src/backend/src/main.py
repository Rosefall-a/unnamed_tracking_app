# app/main.py
from fastapi import FastAPI

from src.api.routes import auth, games, users
from src.api.routes.utils.misc import router as misc_router
from src.core.auth import ensure_primary_user
from src.database.session import SessionLocal

app = FastAPI(
    title="My API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.include_router(games.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(misc_router)


@app.on_event("startup")
async def bootstrap_primary_user() -> None:
    async with SessionLocal() as db:
        await ensure_primary_user(db)


@app.get("/health")
def health():
    return {"status": "ok"}
