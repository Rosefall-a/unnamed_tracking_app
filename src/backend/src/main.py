# app/main.py
import asyncio
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from src.api.routes import (admin_backup,app_integrations,api_keys,auth,bounties,cards,default_game_assets,export_import,game_archives,games,library_sync,media,settings,stats,users)
from src.api.routes import set as set_routes
from src.api.routes.auth_oidc import router as auth_oidc_router
from src.api.routes.deployment_settings import router as deployment_settings_router
from src.api.routes.password_reset import router as password_reset_router
from src.api.routes.session_admin import router as session_admin_router
from src.api.routes.setup import router as setup_router
from src.api.routes.settings import get_or_create_app_integration_settings
from src.api.routes.utils.misc import router as misc_router
from src.core.auth import COOKIE_NAMESPACE
from src.core.config import settings as app_settings
from src.core.data_paths import ensure_data_directories
from src.core.provider_credentials import apply_deployment_provider_credentials
from src.core.runtime_settings import apply_runtime_settings
from src.database.session import SessionLocal
from src.features.backup.scheduler import run_backup_loop
from src.features.trash.sweep import run_sweep_loop
app=FastAPI(title="Archive",docs_url="/api/docs",redoc_url="/api/redoc",openapi_url="/api/openapi.json")
app.add_middleware(SessionMiddleware,secret_key=app_settings.SECRET_KEY,session_cookie=f"oidc_state_{COOKIE_NAMESPACE}",same_site="lax",https_only=app_settings.AUTH_COOKIE_SECURE)
app.include_router(default_game_assets.router);app.include_router(games.router);app.include_router(game_archives.router);app.include_router(users.router);app.include_router(api_keys.router);app.include_router(auth.router);app.include_router(session_admin_router);app.include_router(auth_oidc_router);app.include_router(password_reset_router);app.include_router(setup_router);app.include_router(settings.router);app.include_router(deployment_settings_router);app.include_router(admin_backup.router);app.include_router(app_integrations.router);app.include_router(media.router);app.include_router(stats.router);app.include_router(library_sync.router);app.include_router(bounties.router);app.include_router(export_import.router);app.include_router(set_routes.router);app.include_router(cards.router);app.include_router(misc_router)
@app.on_event("startup")
async def bootstrap_application_settings()->None:
    ensure_data_directories()
    async with SessionLocal() as db:
        app_integrations_row=await get_or_create_app_integration_settings(db)
        if not app_integrations_row.runtime_settings_initialized:
            app_integrations_row.auth_cookie_secure=app_settings.AUTH_COOKIE_SECURE;app_integrations_row.max_upload_size_mb=app_settings.MAX_UPLOAD_SIZE_MB;app_integrations_row.max_clip_size_mb=app_settings.MAX_CLIP_SIZE_MB;app_integrations_row.max_world_save_size_mb=app_settings.MAX_WORLD_SAVE_SIZE_MB;app_integrations_row.runtime_settings_initialized=True;await db.commit()
        apply_runtime_settings(app_integrations_row);apply_deployment_provider_credentials(app_integrations_row)
@app.on_event("startup")
async def start_trash_sweep()->None:asyncio.create_task(run_sweep_loop())
@app.on_event("startup")
async def start_backup_loop()->None:asyncio.create_task(run_backup_loop())
@app.get("/health")
def health():return {"status":"ok"}
