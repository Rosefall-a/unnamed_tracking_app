# app/main.py
import asyncio

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from src.api.routes import (
    app_integrations,
    api_keys,
    auth,
    bounties,
    cards,
    default_game_assets,
    export_import,
    game_archives,
    games,
    library_sync,
    media,
    settings,
    stats,
    users,
)
from src.api.routes import set as set_routes
from src.api.routes.auth_oidc import router as auth_oidc_router
from src.api.routes.deployment_settings import router as deployment_settings_router
from src.api.routes.setup import router as setup_router
from src.api.routes.settings import get_or_create_app_integration_settings
from src.api.routes.utils.misc import router as misc_router
from src.core.auth import ensure_primary_user
from src.core.config import settings as app_settings
from src.core.provider_credentials import apply_deployment_provider_credentials
from src.database.session import SessionLocal
from src.features.backup.scheduler import run_backup_loop
from src.features.trash.sweep import run_sweep_loop

app = FastAPI(
    title="My API", docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)
app.add_middleware(
    SessionMiddleware,
    secret_key=app_settings.SECRET_KEY,
    session_cookie="oidc_state",
    same_site="lax",
    https_only=app_settings.AUTH_COOKIE_SECURE,
)

app.include_router(default_game_assets.router)
app.include_router(games.router)
app.include_router(game_archives.router)
app.include_router(users.router)
app.include_router(api_keys.router)
app.include_router(auth.router)
app.include_router(auth_oidc_router)
app.include_router(setup_router)
app.include_router(settings.router)
app.include_router(deployment_settings_router)
app.include_router(app_integrations.router)
app.include_router(media.router)
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
        if (
            app_settings.PRIMARY_USER_USERNAME.strip()
            and app_settings.PRIMARY_USER_EMAIL.strip()
            and app_settings.PRIMARY_USER_PASSWORD
        ):
            await ensure_primary_user(db)
        app_integrations_row = await get_or_create_app_integration_settings(db)
        apply_deployment_provider_credentials(app_integrations_row)


@app.on_event("startup")
async def start_trash_sweep() -> None:
    asyncio.create_task(run_sweep_loop())


@app.on_event("startup")
async def start_backup_loop() -> None:
    asyncio.create_task(run_backup_loop())


@app.get("/health")
def health():
    return {"status": "ok"}
