# app/main.py
import asyncio

from fastapi import FastAPI

from src.api.routes import auth, bounties, game_archives, games, library_sync, media, settings, stats, users
from src.api.routes.utils.misc import router as misc_router
from src.core.auth import ensure_primary_user
from src.database.session import SessionLocal
from src.features.trash.sweep import run_sweep_loop

app = FastAPI(
    title="My API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.include_router(games.router)
app.include_router(game_archives.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(media.router)
app.include_router(stats.router)
app.include_router(library_sync.router)
app.include_router(bounties.router)
app.include_router(misc_router)


@app.on_event("startup")
async def bootstrap_primary_user() -> None:
    async with SessionLocal() as db:
        await ensure_primary_user(db)


@app.on_event("startup")
async def start_trash_sweep() -> None:
    asyncio.create_task(run_sweep_loop())


@app.get("/health")
def health():
    return {"status": "ok"}
