# app/main.py
import asyncio

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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
from src.api.routes.password_reset import router as password_reset_router
from src.api.routes.smtp_settings import router as smtp_settings_router
from src.api.routes.settings import get_or_create_app_integration_settings
from src.api.routes.utils.misc import router as misc_router
from src.core.auth import ensure_primary_user
from src.core.provider_credentials import apply_deployment_provider_credentials
from src.database.session import SessionLocal
from src.features.backup.scheduler import run_backup_loop
from src.features.trash.sweep import run_sweep_loop

app = FastAPI(
    title="My API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


def _safe_validation_errors(exc: RequestValidationError) -> list[dict[str, object]]:
    return [
        {
            "type": error.get("type", "value_error"),
            "loc": error.get("loc", []),
            "msg": error.get("msg", "Invalid request."),
        }
        for error in exc.errors()
    ]


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    del request
    return JSONResponse(status_code=422, content={"detail": _safe_validation_errors(exc)})


# Register the fallback artwork route before the normal asset route. When a
# stored asset exists it is served unchanged; only a missing key-art file
# reaches the generated default cover.
app.include_router(default_game_assets.router)
app.include_router(games.router)
app.include_router(game_archives.router)
app.include_router(users.router)
app.include_router(api_keys.router)
app.include_router(auth.router)
app.include_router(password_reset_router)
app.include_router(smtp_settings_router)
app.include_router(settings.router)
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
