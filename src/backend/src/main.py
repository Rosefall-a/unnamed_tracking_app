# app/main.py
import asyncio

from fastapi import FastAPI, Request

from src.api.routes import (
    admin_backup,
    anime,
    app_integrations,
    api_keys,
    auth,
    bounties,
    cards,
    calendar_feed,
    default_game_assets,
    export_import,
    game_archives,
    games,
    invitations,
    library_sync,
    media,
    media_extras,
    media_lists,
    media_stats,
    movies,
    notifications,
    preferences,
    settings,
    stats,
    tv_shows,
    users,
)
from src.api.routes import set as set_routes
from src.api.routes.utils.misc import router as misc_router
from src.core.auth import COOKIE_NAMESPACE, ensure_primary_user
from src.core.config import settings as app_settings
from src.core.data_paths import ensure_data_directories
from src.core.provider_credentials import apply_deployment_provider_credentials
from src.core.runtime_settings import apply_runtime_settings
from src.core.crypto import encrypt_secret
from src.database.models.oidc_settings import OidcSettings
from src.database.session import SessionLocal
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware
from src.features.backup.scheduler import run_backup_loop
from src.features.metadata.refresh import run_airing_check_loop, run_metadata_refresh_loop
from src.features.trash.sweep import run_sweep_loop

app = FastAPI(
    title="My API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.include_router(default_game_assets.router)\napp.include_router(games.router)
app.include_router(movies.router)\napp.include_router(tv_shows.router)\napp.include_router(anime.router)
app.include_router(game_archives.router)
app.include_router(users.router)\napp.include_router(api_keys.router)\napp.include_router(session_admin_router)\napp.include_router(auth_oidc_router)\napp.include_router(password_reset_router)\napp.include_router(invitations.router)\napp.include_router(setup_router)\napp.include_router(deployment_settings_router)\napp.include_router(admin_backup.router)\napp.include_router(app_integrations.router)
app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(media.router)\napp.include_router(media_extras.router)\napp.include_router(media_lists.router)\napp.include_router(notifications.router)\napp.include_router(media_stats.router)\napp.include_router(preferences.router)\napp.include_router(calendar_feed.authed_router)\napp.include_router(calendar_feed.public_router)
app.include_router(stats.router)
app.include_router(library_sync.router)
app.include_router(bounties.router)
app.include_router(export_import.router)
app.include_router(set_routes.router)
app.include_router(cards.router)
app.include_router(misc_router)


@app.on_event("startup")
async def bootstrap_primary_user() -> None:
    async with SessionLocal() as db:
        await ensure_primary_user(db)


@app.on_event("startup")
async def start_trash_sweep() -> None:
    asyncio.create_task(run_sweep_loop())


@app.on_event("startup")
async def start_backup_loop() -> None:
    asyncio.create_task(run_backup_loop())


@app.on_event("startup")
async def start_airing_check_loop() -> None:
    asyncio.create_task(run_airing_check_loop())


@app.on_event("startup")
async def start_metadata_refresh_loop() -> None:
    asyncio.create_task(run_metadata_refresh_loop())


@app.get("/health")
def health():
    return {"status": "ok"}
