"""Authorized plugin UI, documents, settings, actions and browser gateway."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
import secrets
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse, JSONResponse

from src.api.routes.session_manager import upload_geoip
from src.core.auth import get_current_user, hash_token, session_cookie_name
from src.database.models.auth import UserSession
from src.database.models.user import User
from src.database.session import get_db
from src.plugin_api.compatibility import is_legacy_contract
from src.plugin_api.contracts import (
    PLUGIN_API_CONTRACT_VERSION,
    Capability,
    CapabilityRef,
    ErrorCode,
    ErrorEnvelope,
    PluginUiDocument,
    plugin_contract_compatibility_reason,
)
from src.plugin_api.documents import DocumentAccessError, document_path, owned_document
from src.plugin_api.frontend_assets import inline_frontend_assets
from src.plugin_api.gateway import dispatch_gateway_request, runtime_token_is_valid
from src.plugin_api.grants import has_capability_grant, installation_is_executable
from src.plugin_api.lifecycle import plugin_contract_active
from src.plugin_api.runtime_client import PluginRuntimeRequestError, PluginRuntimeUnavailable
from src.plugin_api.ui_permissions import filter_ui_document as _filter_ui_document

from . import models, runtime

router = APIRouter(prefix="/api/plugins", tags=["plugins"])
logger = logging.getLogger(__name__)


_GATEWAY_DISPATCH_TIMEOUT = 8.0


_GEOIP_UPLOAD_FILE = File(...)
_PLUGIN_DB = Depends(get_db)
_PLUGIN_USER = Depends(get_current_user)
_PLUGIN_SETTINGS_BODY = Body(default_factory=dict)


_DOCUMENT_DATA_ROOT = Path("/data/users")


_PLUGIN_FRONTEND_CSP = (
    "default-src 'self'; script-src 'self' https://unpkg.com; "
    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; "
    "frame-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'self'"
)


@router.get("/{plugin_id}/frontend/{asset_path:path}")
async def plugin_frontend(
    plugin_id: str,
    asset_path: str,
    db: AsyncSession = _PLUGIN_DB,
    user: User = _PLUGIN_USER,
) -> Response:
    if not asset_path or ".." in Path(asset_path).parts:
        raise HTTPException(status_code=404, detail="Plugin frontend asset not found.")
    await runtime.plugin_and_capabilities(plugin_id, db, user)
    try:
        content = await runtime.client.frontend_asset(quote(plugin_id, safe=""), asset_path)
    except PluginRuntimeRequestError as exc:
        raise HTTPException(status_code=404, detail="Plugin frontend asset not found.") from exc
    except PluginRuntimeUnavailable as exc:
        raise runtime.runtime_error(exc) from exc
    media_type = {".css": "text/css", ".js": "text/javascript", ".html": "text/html"}.get(
        Path(asset_path).suffix.lower(),
        mimetypes.guess_type(asset_path)[0] or "application/octet-stream",
    )
    csp = _PLUGIN_FRONTEND_CSP
    if media_type == "text/html":
        try:
            ui = await runtime.client.plugin_ui(quote(plugin_id, safe=""))
        except PluginRuntimeRequestError as exc:
            raise runtime.runtime_request_error(exc) from exc
        except PluginRuntimeUnavailable as exc:
            raise runtime.runtime_error(exc) from exc
        frontend = ui.get("frontend", {})
        if frontend.get("inline_assets") is True and frontend.get("entry") == asset_path:
            nonce = secrets.token_urlsafe(24)

            async def load_asset(path: str) -> bytes:
                return await runtime.client.frontend_asset(quote(plugin_id, safe=""), path)

            try:
                content = await inline_frontend_assets(content, asset_path, nonce, load_asset)
            except (ValueError, PluginRuntimeRequestError) as exc:
                raise HTTPException(422, "Invalid packaged frontend assets.") from exc
            except PluginRuntimeUnavailable as exc:
                raise runtime.runtime_error(exc) from exc
            csp = csp.replace("script-src 'self'", f"script-src 'nonce-{nonce}' 'self'")
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Security-Policy": csp,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.api_route(
    "/{plugin_id}/capabilities/documents/{document_id}/download", methods=["GET", "HEAD"]
)
async def plugin_document_download(
    plugin_id: str,
    document_id: UUID,
    db: AsyncSession = _PLUGIN_DB,
    user: User = _PLUGIN_USER,
) -> FileResponse:
    """Stream an owned original as an attachment, including unsupported preview types."""
    _, capabilities = await runtime.plugin_and_capabilities(plugin_id, db, user)
    if "documents.read" not in capabilities:
        raise HTTPException(403, "Permission documents.read has not been granted.")
    row = await owned_document(db, user.id, document_id)
    if row is None:
        raise HTTPException(404, "Document not found.")
    item, game = row
    try:
        path = document_path(_DOCUMENT_DATA_ROOT, user.id, game.folder_location, item.filename)
    except DocumentAccessError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    return FileResponse(
        path,
        filename=item.filename.split("_", 1)[-1],
        media_type="application/octet-stream",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/{plugin_id}/native-frontend/{asset_path:path}")
async def plugin_native_frontend(
    plugin_id: str,
    asset_path: str,
    db: AsyncSession = _PLUGIN_DB,
    user: User = _PLUGIN_USER,
) -> Response:
    if not asset_path or ".." in Path(asset_path).parts:
        raise HTTPException(status_code=404, detail="Plugin native frontend asset not found.")
    _, capabilities = await runtime.plugin_and_capabilities(plugin_id, db, user)
    if Capability.FRONTEND_NATIVE.value not in capabilities:
        raise HTTPException(
            status_code=403, detail="Permission frontend.native has not been granted."
        )
    try:
        content = await runtime.client.native_frontend_asset(quote(plugin_id, safe=""), asset_path)
    except PluginRuntimeRequestError as exc:
        raise HTTPException(
            status_code=404, detail="Plugin native frontend asset not found."
        ) from exc
    except PluginRuntimeUnavailable as exc:
        raise runtime.runtime_error(exc) from exc
    media_type = mimetypes.guess_type(asset_path)[0] or "application/octet-stream"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{plugin_id}/ui")
async def plugin_ui(
    plugin_id: str,
    db: AsyncSession = _PLUGIN_DB,
    user: User = _PLUGIN_USER,
) -> dict:
    plugin, capabilities = await runtime.plugin_and_capabilities(plugin_id, db, user)
    try:
        payload = await runtime.client.plugin_ui(quote(plugin_id, safe=""))
    except PluginRuntimeRequestError as exc:
        raise runtime.runtime_request_error(exc) from exc
    except PluginRuntimeUnavailable as exc:
        raise runtime.runtime_error(exc) from exc
    try:
        document = PluginUiDocument.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Rejected invalid plugin UI document: plugin_id=%s", plugin_id)
        raise HTTPException(status_code=422, detail="Plugin UI document is invalid.") from exc
    if document.plugin_id != plugin_id:
        raise HTTPException(status_code=422, detail="Plugin UI document identity is invalid.")
    if plugin_contract_compatibility_reason(
        document.api_contract_version, allow_legacy=plugin.get("legacy_compatibility") is True
    ) or document.api_contract_version != plugin.get("api_contract_version", "1.0.0"):
        raise HTTPException(
            status_code=409, detail="Plugin UI and manifest API contracts must match."
        )
    if is_legacy_contract(document.api_contract_version):
        document = document.model_copy(
            update={
                "native_frontend": None,
                "themes": (),
                "home_widgets": (),
                "shortcuts": (),
                "navigation": tuple(
                    item.model_copy(update={"group": "Extensions", "folders": ()})
                    for item in document.navigation
                ),
                "settings_sections": tuple(
                    item.model_copy(update={"group": "Extensions", "folders": ()})
                    for item in document.settings_sections
                ),
            }
        )
    return _filter_ui_document(document, capabilities).model_dump(mode="json")


@router.put("/{plugin_id}/secrets/{key}")
async def save_plugin_secret(
    plugin_id: str,
    key: str,
    payload: dict[str, str] = _PLUGIN_SETTINGS_BODY,
    db: AsyncSession = _PLUGIN_DB,
    user: User = _PLUGIN_USER,
) -> dict[str, Any]:
    if not key or len(key) > 128 or "/" in key or ".." in key:
        raise HTTPException(status_code=400, detail="Invalid plugin secret key.")
    plugin = await runtime.live_plugin(plugin_id)
    if not await has_capability_grant(
        db,
        plugin_id=plugin_id,
        installation_id=UUID(str(plugin["installation_id"])),
        capability="plugin.storage",
        user_id=user.id,
    ):
        raise HTTPException(
            status_code=403, detail="Permission plugin.storage has not been granted."
        )
    value = payload.get("value")
    if not isinstance(value, str) or not value:
        raise HTTPException(status_code=400, detail="Secret value must be a non-empty string.")
    try:
        await runtime.client.save_secret(quote(plugin_id, safe=""), f"secrets/{key}", value)
    except PluginRuntimeUnavailable as exc:
        raise runtime.runtime_error(exc) from exc
    logger.info(
        "Plugin secret updated: plugin_id=%s installation_id=%s key=%s user_id=%s",
        plugin_id,
        plugin["installation_id"],
        key,
        user.id,
    )
    return {"plugin_id": plugin_id, "key": key, "saved": True}


@router.put("/{plugin_id}/settings")
async def save_plugin_settings(
    plugin_id: str,
    payload: dict[str, Any] = _PLUGIN_SETTINGS_BODY,
    db: AsyncSession = _PLUGIN_DB,
    user: User = _PLUGIN_USER,
) -> dict:
    plugin = await runtime.live_plugin(plugin_id)
    if not await has_capability_grant(
        db,
        plugin_id=plugin_id,
        installation_id=UUID(str(plugin["installation_id"])),
        capability="plugin.settings",
        user_id=user.id,
    ):
        raise HTTPException(
            status_code=403, detail="Permission plugin.settings has not been granted."
        )
    try:
        await runtime.client.save_settings(quote(plugin_id, safe=""), payload)
    except PluginRuntimeUnavailable as exc:
        raise runtime.runtime_error(exc) from exc
    return {"plugin_id": plugin_id, "saved": True}


async def current_browser_session_id(
    db: AsyncSession, user_id: UUID, request: Request
) -> str | None:
    """Resolve a non-secret session identifier from authenticated host cookies."""
    token = request.cookies.get(session_cookie_name(request.headers.get("host", "")))
    if not token:
        return None
    session_id = await db.scalar(
        select(UserSession.id).where(
            UserSession.user_id == user_id,
            UserSession.token_hash == hash_token(token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > int(time.time()),
        )
    )
    return str(session_id) if session_id else None


@router.post("/{plugin_id}/capabilities/sessions/geoip")
async def plugin_geoip_upload(
    plugin_id: str,
    *,
    file: UploadFile = _GEOIP_UPLOAD_FILE,
    kind: str = Query(default="city", pattern="^(city|country|network)$"),
    confirmed: bool = Query(default=False),
    db: AsyncSession = runtime.PLUGIN_DB,
    admin: User = runtime.PLUGIN_ADMIN,
) -> dict[str, object]:
    """Allow enabled plugins with a narrow grant to replace a local GeoIP database."""
    plugin = await runtime.live_plugin(plugin_id)
    if not await has_capability_grant(
        db,
        plugin_id=plugin_id,
        installation_id=UUID(str(plugin["installation_id"])),
        capability="sessions.geoip.configure",
        user_id=admin.id,
    ):
        raise HTTPException(403, "Permission sessions.geoip.configure has not been granted.")
    if not confirmed:
        raise HTTPException(409, "Explicit GeoIP replacement confirmation is required.")
    result = await upload_geoip(file=file, kind=kind, admin=admin)
    return {"configured": result["configured"], "kind": kind}


async def _authorize_action(
    plugin_id: str,
    action_id: str,
    payload: models.PluginActionIn,
    *,
    db: AsyncSession,
    plugin: dict[str, Any],
    user: User,
) -> tuple[dict[str, Any], UUID]:
    document = await runtime.client.plugin_ui(quote(plugin_id, safe=""))
    action = next(
        (item for item in document.get("actions", []) if item.get("id") == action_id), None
    )
    if action is None:
        raise HTTPException(status_code=404, detail="Plugin action not found.")
    installation_id = UUID(str(plugin.get("installation_id")))
    capability_ref = action.get("capability")
    if capability_ref is not None:
        try:
            reference = CapabilityRef.model_validate(capability_ref)
        except ValidationError as exc:
            raise HTTPException(
                status_code=422, detail="Plugin action capability is invalid."
            ) from exc
        capability = reference.name.value
        if not await has_capability_grant(
            db,
            plugin_id=plugin_id,
            installation_id=installation_id,
            capability=capability,
            user_id=user.id,
            capability_version=reference.version,
        ):
            raise HTTPException(
                status_code=403, detail=f"Permission {capability} has not been granted."
            )
    if action.get("confirmation") and getattr(payload, "confirmed", False) is not True:
        raise HTTPException(status_code=409, detail="Explicit action confirmation is required.")
    return document, installation_id


async def _host_action_context(
    plugin_id: str,
    action_id: str,
    payload: models.PluginActionIn,
    *,
    db: AsyncSession,
    document: dict[str, Any],
    installation_id: UUID,
    user: User,
    request: Request,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "path": f"/plugins/{plugin_id}",
        "user_id": str(user.id),
    }
    action_context = getattr(payload, "context", None)
    if action_context is not None:
        navigation_location = {
            "game": "game.context",
            "media": "media.context",
            "documents": None,
        }[action_context.kind]
        contextual_action = next(
            (
                item
                for item in document.get("contextual_actions", [])
                if item.get("action_id") == action_id
                and item.get("location") == action_context.kind
            ),
            None,
        )
        contextual_navigation = next(
            (
                item
                for item in document.get("navigation", [])
                if item.get("action_id") == action_id
                and item.get("location") == navigation_location
            ),
            None,
        )
        if contextual_action is None and contextual_navigation is None:
            raise HTTPException(
                status_code=403,
                detail="The action is not declared for this host context.",
            )
        context_capability = f"frontend.context.{action_context.kind}"
        if not await has_capability_grant(
            db,
            plugin_id=plugin_id,
            installation_id=installation_id,
            capability=context_capability,
            user_id=user.id,
        ):
            raise HTTPException(
                status_code=403,
                detail=f"Permission {context_capability} has not been granted.",
            )
        context.update(
            {
                "kind": action_context.kind,
                "resource_id": action_context.resource_id,
            }
        )
        if action_context.resource_type is not None:
            context["resource_type"] = action_context.resource_type
    context["confirmed"] = getattr(payload, "confirmed", False)
    context["is_admin"] = bool(getattr(user, "is_admin", False))
    session_id = await current_browser_session_id(db, user.id, request)
    if session_id:
        context["session_id"] = session_id
    return context


@router.post(
    "/{plugin_id}/actions/{action_id}", dependencies=[Depends(runtime.private_plugin_response)]
)
async def plugin_action(
    plugin_id: str,
    action_id: str,
    payload: models.PluginActionIn,
    db: AsyncSession = _PLUGIN_DB,
    user: User = _PLUGIN_USER,
    *,
    request: Request,
) -> dict:
    """Authorize a declared action and supply host-owned authentication context."""
    request_id = uuid4()
    plugin = await runtime.live_plugin(plugin_id)
    document, installation_id = await _authorize_action(
        plugin_id, action_id, payload, db=db, plugin=plugin, user=user
    )
    values = dict(payload.values)
    values.pop("_plugin_context", None)
    context = await _host_action_context(
        plugin_id,
        action_id,
        payload,
        db=db,
        document=document,
        installation_id=installation_id,
        user=user,
        request=request,
    )
    values["_plugin_context"] = context
    try:
        result = await runtime.client.action(
            quote(plugin_id, safe=""), quote(action_id, safe=""), values, user_id=str(user.id)
        )
    except PluginRuntimeRequestError as exc:
        raise runtime.runtime_request_error(exc) from exc
    except PluginRuntimeUnavailable as exc:
        raise runtime.runtime_error(exc) from exc
    logger.info(
        "Plugin action completed: request_id=%s plugin_id=%s installation_id=%s action_id=%s user_id=%s",
        request_id,
        plugin_id,
        installation_id,
        action_id,
        user.id,
    )
    return {
        **(result or {"completed": True}),
        "plugin_id": plugin_id,
        "action": action_id,
        "request_id": str(request_id),
    }


async def _gateway_user_context(
    db: AsyncSession,
    payload: models.PluginGatewayIn,
    failure: Callable[[int, ErrorCode, str], JSONResponse],
) -> User | JSONResponse:
    try:
        plugin = await runtime.live_plugin(payload.plugin_id, require_enabled=False)
    except HTTPException as exc:
        code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.UNAVAILABLE
        return failure(exc.status_code, code, str(exc.detail))
    starting_authorization = (
        payload.method == "capabilities.check"
        and plugin_contract_active(plugin)
        and plugin.get("enabled") is True
        and plugin.get("compatible") is True
        and plugin.get("status") == "starting"
        and plugin.get("health") in {"healthy", "unknown"}
    )
    if not installation_is_executable(plugin) and not starting_authorization:
        return failure(409, ErrorCode.CONFLICT, "Plugin installation is not executable.")
    if UUID(str(plugin["installation_id"])) != payload.installation_id:
        return failure(409, ErrorCode.CONFLICT, "Plugin installation identity does not match.")
    user = await db.scalar(select(User).where(User.id == payload.user_id, User.is_active.is_(True)))
    if user is None:
        return failure(403, ErrorCode.FORBIDDEN, "Active user context is required.")
    return user


async def _dispatch_gateway(
    db: AsyncSession,
    payload: models.PluginGatewayIn,
    failure: Callable[[int, ErrorCode, str], JSONResponse],
) -> dict[str, Any] | JSONResponse:
    try:
        # Complete before the runtime bridge's ten-second transport deadline.
        async with asyncio.timeout(_GATEWAY_DISPATCH_TIMEOUT):
            result = await dispatch_gateway_request(
                db,
                plugin_id=payload.plugin_id,
                user_id=payload.user_id,
                installation_id=payload.installation_id,
                method=payload.method,
                capability=payload.capability,
                capability_version=payload.capability_version,
                payload=payload.payload,
            )
    except PermissionError as exc:
        return failure(403, ErrorCode.FORBIDDEN, str(exc))
    except (ValueError, LookupError) as exc:
        return failure(422, ErrorCode.INVALID_REQUEST, str(exc))
    except TimeoutError:
        return failure(504, ErrorCode.UNAVAILABLE, "Plugin gateway operation timed out.")
    # Convert an unexpected host failure into the bounded gateway error contract.
    # pylint: disable-next=broad-exception-caught
    except Exception:
        logger.exception("Plugin gateway failure: request_id=%s", payload.request_id)
        return failure(500, ErrorCode.INTERNAL, "Plugin gateway operation failed.")
    return {"api_version": "v1", "request_id": str(payload.request_id), "payload": result}


@router.post(
    "/runtime/gateway",
    dependencies=[Depends(runtime.private_plugin_response)],
    response_model=None,
)
async def plugin_gateway(
    payload: models.PluginGatewayIn,
    db: AsyncSession = _PLUGIN_DB,
    runtime_token: str | None = Header(default=None, alias="X-Plugin-Runtime-Token"),
) -> dict[str, Any] | JSONResponse:
    def failure(status: int, code: ErrorCode, message: str) -> JSONResponse:
        envelope = ErrorEnvelope(code=code, message=message[:1024], request_id=payload.request_id)
        response = JSONResponse(
            status_code=status,
            content={"detail": message, "error": envelope.model_dump(mode="json")},
        )
        runtime.private_plugin_response(response)
        return response

    if not runtime_token_is_valid(runtime_token):
        return failure(503, ErrorCode.UNAVAILABLE, "Plugin runtime gateway is not configured.")
    if payload.api_version != "v1":
        return failure(
            409, ErrorCode.INCOMPATIBLE, "Unsupported Plugin API version; supported: v1."
        )
    user = await _gateway_user_context(db, payload, failure)
    if isinstance(user, JSONResponse):
        return user
    logger.info(
        "Plugin gateway dispatch: request_id=%s plugin_id=%s installation_id=%s method=%s capability=%s user_id=%s",
        payload.request_id,
        payload.plugin_id,
        payload.installation_id,
        payload.method,
        payload.capability,
        payload.user_id,
    )
    return await _dispatch_gateway(db, payload, failure)


@router.get("/runtime/health")
async def runtime_health(admin: User = runtime.PLUGIN_ADMIN) -> dict:
    del admin
    try:
        health = await runtime.client.health()
    except (PluginRuntimeUnavailable, PluginRuntimeRequestError) as exc:
        health = {
            "available": False,
            "bubblewrap_available": None,
            "sandbox_available": False,
            "mechanism": "unavailable",
            "last_error": str(exc),
        }
    versions = {
        "host_api_contract_version": PLUGIN_API_CONTRACT_VERSION,
        "host_sdk_version": os.getenv("PLUGIN_SDK_VERSION", PLUGIN_API_CONTRACT_VERSION),
        "host_application_version": os.getenv("PLUGIN_APPLICATION_VERSION", "1.0.0"),
    }
    failures = []
    if health.get("available", True):
        for label, runtime_key, host_key in (
            ("Plugin API", "api_contract_version", "host_api_contract_version"),
            ("SDK", "sdk_version", "host_sdk_version"),
            ("Application compatibility", "application_version", "host_application_version"),
        ):
            reported = health.get(runtime_key)
            if reported is None:
                failures.append(f"Runtime does not report its {label} version.")
            elif reported != versions[host_key]:
                failures.append(
                    f"{label} version mismatch: host {versions[host_key]}, runtime {reported}."
                )
    return {
        **health,
        **versions,
        "version_health": "unavailable"
        if not health.get("available", True)
        else "incompatible"
        if failures
        else "healthy",
        "version_error": " ".join(failures) or None,
    }
