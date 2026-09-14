# app/main.py
import asyncio
import json
from urllib.parse import urlparse

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from src.api.routes import (
    admin_backup,
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
from src.api.routes.password_reset import router as password_reset_router
from src.api.routes.session_admin import router as session_admin_router
from src.api.routes.setup import router as setup_router
from src.api.routes.settings import get_or_create_app_integration_settings
from src.api.routes.utils.misc import router as misc_router
from src.core.auth import COOKIE_NAMESPACE
from src.core.config import settings as app_settings
from src.core.crypto import encrypt_secret
from src.core.data_paths import ensure_data_directories
from src.core.provider_credentials import apply_deployment_provider_credentials
from src.core.runtime_settings import apply_runtime_settings
from src.database.models.oidc_settings import OidcSettings
from src.database.session import SessionLocal
from src.features.backup.scheduler import run_backup_loop
from src.features.trash.sweep import run_sweep_loop

app = FastAPI(
    title="Archive", docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)
app.add_middleware(
    SessionMiddleware,
    secret_key=app_settings.SECRET_KEY,
    session_cookie=f"oidc_state_{COOKIE_NAMESPACE}",
    same_site="lax",
    https_only=app_settings.AUTH_COOKIE_SECURE,
)
app.include_router(default_game_assets.router)
app.include_router(games.router)
app.include_router(game_archives.router)
app.include_router(users.router)
app.include_router(api_keys.router)
app.include_router(auth.router)
app.include_router(session_admin_router)
app.include_router(auth_oidc_router)
app.include_router(password_reset_router)
app.include_router(setup_router)
app.include_router(settings.router)
app.include_router(deployment_settings_router)
app.include_router(admin_backup.router)
app.include_router(app_integrations.router)
app.include_router(media.router)
app.include_router(stats.router)
app.include_router(library_sync.router)
app.include_router(bounties.router)
app.include_router(export_import.router)
app.include_router(set_routes.router)
app.include_router(cards.router)
app.include_router(misc_router)


def _legacy_oidc_provider() -> dict[str, object] | None:
    """Build a named provider from the legacy OIDC environment settings."""
    if not (
        app_settings.OIDC_ISSUER_URL
        and app_settings.OIDC_CLIENT_ID
        and app_settings.OIDC_CLIENT_SECRET
    ):
        return None
    issuer = app_settings.OIDC_ISSUER_URL.strip()
    hostname = (urlparse(issuer).hostname or "oidc").lower()
    name = hostname.split(".")[0] or "OIDC"
    slug = "".join(char if char.isalnum() else "-" for char in name).strip("-") or "oidc"
    return {
        "name": name,
        "slug": slug[:80],
        "issuer_url": issuer,
        "client_id": app_settings.OIDC_CLIENT_ID,
        "client_secret": encrypt_secret(app_settings.OIDC_CLIENT_SECRET),
        "scopes": app_settings.OIDC_SCOPES or "openid profile email",
        "redirect_uri": app_settings.OIDC_REDIRECT_URI,
        "groups_claim": app_settings.OIDC_GROUPS_CLAIM or "groups",
        "admin_group": app_settings.OIDC_ADMIN_GROUP,
        "user_match_field": getattr(app_settings, "OIDC_USER_MATCH_FIELD", "email"),
        "allow_new_users": True,
        "button_text": "Continue with SSO",
        "button_image_url": None,
        "enabled": True,
        "show_on_login": True,
    }


async def _migrate_legacy_oidc(db) -> None:
    """Move legacy .env OIDC settings into the database-backed Settings UI.

    Existing installations historically configured one OIDC provider with
    OIDC_* environment variables. Keep those variables as a runtime fallback,
    but copy a configured legacy provider into the new database representation
    on upgrade so it appears in Settings and in deployment backups.
    """
    legacy = _legacy_oidc_provider()
    if legacy is None:
        return

    row = await db.scalar(__import__("sqlalchemy").select(OidcSettings).limit(1))
    if row is None:
        row = OidcSettings()
        db.add(row)
        await db.flush()

    has_legacy = bool(row.issuer_url and row.client_id and row.client_secret)
    try:
        existing_providers = json.loads(row.providers_json or "[]")
    except (TypeError, ValueError):
        existing_providers = []
    if not isinstance(existing_providers, list):
        existing_providers = []

    if has_legacy or existing_providers:
        return

    row.issuer_url = str(legacy["issuer_url"])
    row.client_id = str(legacy["client_id"])
    row.client_secret = str(legacy["client_secret"])
    row.scopes = str(legacy["scopes"])
    row.redirect_uri = legacy["redirect_uri"]
    row.groups_claim = str(legacy["groups_claim"])
    row.admin_group = legacy["admin_group"]
    row.user_match_field = str(legacy["user_match_field"])
    row.login_button_text = str(legacy["button_text"])
    row.allow_new_users = bool(legacy["allow_new_users"])
    row.providers_json = json.dumps([legacy])
    await db.commit()


@app.on_event("startup")
async def bootstrap_application_settings() -> None:
    ensure_data_directories()
    async with SessionLocal() as db:
        app_integrations_row = await get_or_create_app_integration_settings(db)
        if not app_integrations_row.runtime_settings_initialized:
            app_integrations_row.auth_cookie_secure = app_settings.AUTH_COOKIE_SECURE
            app_integrations_row.max_upload_size_mb = app_settings.MAX_UPLOAD_SIZE_MB
            app_integrations_row.max_clip_size_mb = app_settings.MAX_CLIP_SIZE_MB
            app_integrations_row.max_world_save_size_mb = app_settings.MAX_WORLD_SAVE_SIZE_MB
            app_integrations_row.runtime_settings_initialized = True
            await db.commit()
        await _migrate_legacy_oidc(db)
        apply_runtime_settings(app_integrations_row)
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
