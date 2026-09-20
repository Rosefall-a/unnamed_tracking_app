import asyncio
import json
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware

from src.api.routes import (
    admin_backup, anime, app_integrations, api_keys, auth, bounties, cards,
    calendar_feed, default_game_assets, export_import, game_archives, games,
    invitations, library_sync, media, media_extras, media_lists, media_stats,
    movies, notifications, preferences, settings, stats, tv_shows, users,
)
from src.api.routes import set as set_routes
from src.api.routes.auth_oidc import router as auth_oidc_router
from src.api.routes.deployment_settings import router as deployment_settings_router
from src.api.routes.password_reset import router as password_reset_router
from src.api.routes.session_admin import router as session_admin_router
from src.api.routes.setup import router as setup_router
from src.api.routes.settings import get_or_create_app_integration_settings
from src.api.routes.utils.misc import router as misc_router
from src.core.auth import COOKIE_NAMESPACE, ensure_primary_user
from src.core.config import settings as app_settings
from src.core.crypto import encrypt_secret
from src.core.data_paths import ensure_data_directories
from src.core.provider_credentials import apply_deployment_provider_credentials
from src.core.runtime_settings import apply_runtime_settings
from src.database.models.oidc_settings import OidcSettings
from src.database.session import SessionLocal
from src.features.auth.cleanup import cleanup_expired_authentication_records
from src.features.backup.scheduler import run_backup_loop
from src.features.metadata.refresh import run_airing_check_loop, run_metadata_refresh_loop
from src.features.trash.sweep import run_sweep_loop

app = FastAPI(
    title="Archive",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    SessionMiddleware,
    secret_key=app_settings.SECRET_KEY,
    session_cookie=f"oidc_state_{COOKIE_NAMESPACE}",
    same_site="lax",
    https_only=app_settings.AUTH_COOKIE_SECURE,
)


def _safe_validation_errors(exc: RequestValidationError) -> list[dict[str, object]]:
    return [
        {"type": error.get("type", "value_error"), "loc": error.get("loc", []),
         "msg": error.get("msg", "Invalid request.")}
        for error in exc.errors()
    ]


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    del request
    return JSONResponse(status_code=422, content={"detail": _safe_validation_errors(exc)})


def _provider_identity(issuer: str, fallback_name: str = "OIDC") -> tuple[str, str]:
    hostname = (urlparse(issuer).hostname or "").lower()
    name = hostname.split(".")[0] or fallback_name
    slug = "".join(char if char.isalnum() else "-" for char in name).strip("-") or "oidc"
    return name, slug[:80]


def _legacy_oidc_provider_from_env() -> dict[str, object] | None:
    if not (app_settings.OIDC_ISSUER_URL and app_settings.OIDC_CLIENT_ID and app_settings.OIDC_CLIENT_SECRET):
        return None
    issuer = app_settings.OIDC_ISSUER_URL.strip()
    name, slug = _provider_identity(issuer)
    return {
        "name": name, "slug": slug, "issuer_url": issuer,
        "client_id": app_settings.OIDC_CLIENT_ID,
        "client_secret": encrypt_secret(app_settings.OIDC_CLIENT_SECRET),
        "scopes": app_settings.OIDC_SCOPES or "openid profile email",
        "redirect_uri": app_settings.OIDC_REDIRECT_URI,
        "groups_claim": app_settings.OIDC_GROUPS_CLAIM or "groups",
        "admin_group": app_settings.OIDC_ADMIN_GROUP,
        "user_match_field": getattr(app_settings, "OIDC_USER_MATCH_FIELD", "email"),
        "allow_new_users": True, "button_text": "Continue with SSO",
        "button_image_url": None, "enabled": True, "show_on_login": True,
    }


def _legacy_oidc_provider_from_row(row: OidcSettings) -> dict[str, object] | None:
    if not (row.issuer_url and row.client_id and row.client_secret):
        return None
    issuer = row.issuer_url.strip()
    name, slug = _provider_identity(issuer)
    return {
        "name": name, "slug": slug, "issuer_url": issuer,
        "client_id": row.client_id, "client_secret": row.client_secret,
        "scopes": row.scopes or "openid profile email", "redirect_uri": row.redirect_uri,
        "groups_claim": row.groups_claim or "groups", "admin_group": row.admin_group,
        "user_match_field": row.user_match_field or "email",
        "allow_new_users": row.allow_new_users,
        "button_text": row.login_button_text.strip() or "Continue with SSO",
        "button_image_url": None, "enabled": True, "show_on_login": True,
    }


async def _migrate_legacy_oidc(db) -> None:
    row = await db.scalar(select(OidcSettings).limit(1))
    if row is None:
        row = OidcSettings()
        db.add(row)
        await db.flush()
    try:
        existing = json.loads(row.providers_json or "[]")
    except (TypeError, ValueError):
        existing = []
    if not isinstance(existing, list):
        existing = []
    if existing:
        return
    provider = _legacy_oidc_provider_from_row(row) or _legacy_oidc_provider_from_env()
    if provider is None:
        return
    if not row.issuer_url:
        row.issuer_url = str(provider["issuer_url"])
        row.client_id = str(provider["client_id"])
        row.client_secret = str(provider["client_secret"])
        row.scopes = str(provider["scopes"])
        row.redirect_uri = provider["redirect_uri"]
        row.groups_claim = str(provider["groups_claim"])
        row.admin_group = provider["admin_group"]
        row.user_match_field = str(provider["user_match_field"])
        row.login_button_text = str(provider["button_text"])
        row.allow_new_users = bool(provider["allow_new_users"])
    row.providers_json = json.dumps([provider])
    await db.commit()


@app.on_event("startup")
async def bootstrap_application_settings() -> None:
    ensure_data_directories()
    async with SessionLocal() as db:
        row = await get_or_create_app_integration_settings(db)
        if not row.runtime_settings_initialized:
            row.auth_cookie_secure = app_settings.AUTH_COOKIE_SECURE
            row.max_upload_size_mb = app_settings.MAX_UPLOAD_SIZE_MB
            row.max_clip_size_mb = app_settings.MAX_CLIP_SIZE_MB
            row.max_world_save_size_mb = app_settings.MAX_WORLD_SAVE_SIZE_MB
            row.runtime_settings_initialized = True
            await db.commit()
        await _migrate_legacy_oidc(db)
        apply_runtime_settings(row)
        apply_deployment_provider_credentials(row)


@app.on_event("startup")
async def bootstrap_primary_user() -> None:
    async with SessionLocal() as db:
        await ensure_primary_user(db)


@app.on_event("startup")
async def start_auth_cleanup() -> None:
    try:
        async with SessionLocal() as db:
            await cleanup_expired_authentication_records(db)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Authentication record cleanup failed")


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


app.include_router(default_game_assets.router)
app.include_router(games.router)
app.include_router(movies.router)
app.include_router(tv_shows.router)
app.include_router(anime.router)
app.include_router(game_archives.router)
app.include_router(users.router)
app.include_router(api_keys.router)
app.include_router(auth.router)
app.include_router(session_admin_router)
app.include_router(auth_oidc_router)
app.include_router(password_reset_router)
app.include_router(invitations.router)
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
app.include_router(media_extras.router)
app.include_router(media_lists.router)
app.include_router(notifications.router)
app.include_router(media_stats.router)
app.include_router(preferences.router)
app.include_router(calendar_feed.authed_router)
app.include_router(calendar_feed.public_router)
app.include_router(set_routes.router)
app.include_router(cards.router)
app.include_router(misc_router)


@app.get("/health")
def health():
    return {"status": "ok"}
