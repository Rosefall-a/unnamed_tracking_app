"""Authorized plugin-defined backend routes and their request envelopes."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.auth import get_current_user
from src.database.models.user import User
from src.database.session import get_db
from src.plugin_api.backend_routes import (
    BackendRouteConflictError,
    ResolvedBackendRoute,
    resolve_backend_route,
    validate_host_route_ownership,
)
from src.plugin_api.contracts import BackendRouteAuthorization, BackendRouteScope, Capability
from src.plugin_api.grants import has_capability_grant, installation_is_executable
from src.plugin_api.runtime_client import PluginRuntimeRequestError, PluginRuntimeUnavailable
from starlette.responses import JSONResponse

from . import contributions, models, runtime

router = APIRouter(prefix="/api/plugins", tags=["plugins"])
host_router = APIRouter(tags=["plugin-host-routes"])
logger = logging.getLogger(__name__)


_MAX_PLUGIN_ROUTE_BODY_BYTES = 48 * 1024


_MAX_PLUGIN_ROUTE_ENVELOPE_BYTES = 64 * 1024


_PLUGIN_DB = Depends(get_db)


def _backend_route_error(
    status_code: int, code: str, message: str, request_id: UUID
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "api_version": "v1",
            "code": code,
            "message": message,
            "request_id": str(request_id),
        },
    )


async def _backend_route_request(
    request: Request,
    path_parameters: dict[str, str],
    request_id: UUID | None = None,
) -> dict[str, Any]:
    error_request_id = request_id or uuid4()
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > _MAX_PLUGIN_ROUTE_BODY_BYTES:
                raise _backend_route_error(
                    413,
                    "invalid_request",
                    "Plugin request body exceeds 48 KiB.",
                    error_request_id,
                )
        except ValueError as exc:
            raise _backend_route_error(
                400,
                "invalid_request",
                "Content-Length must be an integer.",
                error_request_id,
            ) from exc
    raw_body = await request.body()
    if len(raw_body) > _MAX_PLUGIN_ROUTE_BODY_BYTES:
        raise _backend_route_error(
            413,
            "invalid_request",
            "Plugin request body exceeds 48 KiB.",
            error_request_id,
        )
    body: dict[str, Any] | None = None
    if raw_body:
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise _backend_route_error(
                415,
                "invalid_request",
                "Plugin backend routes accept JSON request bodies.",
                error_request_id,
            )
        try:
            decoded = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _backend_route_error(
                400,
                "invalid_request",
                "Plugin request body is not valid JSON.",
                error_request_id,
            ) from exc
        if not isinstance(decoded, dict):
            raise _backend_route_error(
                422,
                "invalid_request",
                "Plugin request body must be a JSON object.",
                error_request_id,
            )
        body = decoded
    payload = {
        "method": request.method,
        "path": request.url.path,
        "path_parameters": path_parameters,
        "query": {
            key: request.query_params.getlist(key) for key in sorted(request.query_params.keys())
        },
        "headers": {
            key: request.headers[key]
            for key in ("accept", "content-type")
            if key in request.headers
        },
        "body": body,
    }
    if len(json.dumps(payload, separators=(",", ":")).encode("utf-8")) > (
        _MAX_PLUGIN_ROUTE_ENVELOPE_BYTES
    ):
        raise _backend_route_error(
            413,
            "invalid_request",
            "Plugin request exceeds the 64 KiB route limit.",
            error_request_id,
        )
    return payload


async def _resolve_plugin_backend_route(
    *,
    scope: BackendRouteScope,
    route_path: str,
    method: str,
    request_id: UUID,
    plugin_id: str | None = None,
) -> ResolvedBackendRoute:
    """Resolve the single installation that owns a declared request path."""

    try:
        installed_plugins = await runtime._client.plugins()
        if scope is BackendRouteScope.HOST:
            validate_host_route_ownership(installed_plugins)
        resolved = resolve_backend_route(
            installed_plugins,
            scope=scope,
            path=route_path,
            method=method,
            plugin_id=plugin_id,
        )
    except BackendRouteConflictError as exc:
        logger.error("Plugin backend route ownership conflict: path=%s error=%s", route_path, exc)
        raise _backend_route_error(409, "conflict", str(exc), request_id) from exc
    except PluginRuntimeRequestError as exc:
        raise runtime._runtime_request_error(exc) from exc
    except PluginRuntimeUnavailable as exc:
        raise runtime._runtime_error(exc) from exc
    if resolved is None:
        raise _backend_route_error(404, "not_found", "Plugin backend route not found.", request_id)
    return resolved


def _route_installation(resolved: ResolvedBackendRoute, request_id: UUID) -> tuple[str, UUID]:
    """Validate live installation identity and lifecycle state."""

    plugin = resolved.plugin
    owner_id = str(plugin.get("plugin_id", ""))
    installation_value = plugin.get("installation_id")
    if not installation_value:
        raise _backend_route_error(
            409, "unavailable", "Plugin installation identity is missing.", request_id
        )
    try:
        installation_id = UUID(str(installation_value))
    except ValueError as exc:
        raise _backend_route_error(
            409, "unavailable", "Plugin installation identity is invalid.", request_id
        ) from exc
    if not installation_is_executable(plugin):
        logger.warning(
            "Plugin backend route unavailable: request_id=%s plugin_id=%s "
            "installation_id=%s route_id=%s",
            request_id,
            owner_id,
            installation_id,
            resolved.route.id,
        )
        raise _backend_route_error(
            409, "unavailable", "Plugin is not available to serve backend routes.", request_id
        )
    return owner_id, installation_id


async def _authorize_plugin_backend_route(
    db: AsyncSession,
    *,
    resolved: ResolvedBackendRoute,
    scope: BackendRouteScope,
    user: User,
    request_id: UUID,
) -> tuple[str, UUID]:
    """Enforce host authorization policy and the installation-scoped capability grant."""

    owner_id, installation_id = _route_installation(resolved, request_id)
    if resolved.route.authorization is BackendRouteAuthorization.ADMIN and not getattr(
        user, "is_admin", False
    ):
        logger.warning(
            "Plugin backend route denied: request_id=%s plugin_id=%s installation_id=%s "
            "route_id=%s authorization=admin user_id=%s",
            request_id,
            owner_id,
            installation_id,
            resolved.route.id,
            user.id,
        )
        raise _backend_route_error(403, "forbidden", "Administrator access required.", request_id)

    required_capability = (
        Capability.BACKEND_ROUTES_PLUGIN
        if scope is BackendRouteScope.PLUGIN
        else Capability.BACKEND_ROUTES_HOST
    )
    if not await has_capability_grant(
        db,
        plugin_id=owner_id,
        installation_id=installation_id,
        capability=required_capability.value,
        user_id=user.id,
    ):
        logger.warning(
            "Plugin backend route denied: request_id=%s plugin_id=%s installation_id=%s "
            "route_id=%s capability=%s user_id=%s",
            request_id,
            owner_id,
            installation_id,
            resolved.route.id,
            required_capability.value,
            user.id,
        )
        raise _backend_route_error(
            403,
            "forbidden",
            f"Permission {required_capability.value} has not been granted.",
            request_id,
        )
    return owner_id, installation_id


async def _execute_plugin_backend_route(
    request: Request,
    *,
    resolved: ResolvedBackendRoute,
    owner_id: str,
    user: User,
    request_id: UUID,
    db: AsyncSession,
) -> models.PluginBackendRouteResponse:
    """Execute one bounded runtime handler and validate its JSON response."""

    route_request = await _backend_route_request(request, resolved.path_parameters, request_id)
    route_request["current_session_id"] = await contributions._current_browser_session_id(
        db, user.id, request
    )
    route_request["user"] = {
        "id": str(user.id),
        "username": str(getattr(user, "username", "")),
        "is_admin": bool(getattr(user, "is_admin", False)),
    }
    try:
        raw_result = await runtime._client.route(
            owner_id,
            resolved.route.id,
            route_request,
            user_id=str(user.id),
        )
        result = models.PluginBackendRouteResponse.model_validate(raw_result)
        json.dumps(result.body, allow_nan=False)
    except (TypeError, ValueError, ValidationError) as exc:
        logger.warning(
            "Plugin backend route returned an invalid response: request_id=%s plugin_id=%s "
            "route_id=%s",
            request_id,
            owner_id,
            resolved.route.id,
        )
        raise _backend_route_error(
            502, "invalid_request", "Plugin returned an invalid route response.", request_id
        ) from exc
    except PluginRuntimeRequestError as exc:
        logger.warning(
            "Plugin backend route execution failed: request_id=%s plugin_id=%s route_id=%s",
            request_id,
            owner_id,
            resolved.route.id,
        )
        raise _backend_route_error(
            502, "unavailable", "Plugin backend route is unavailable.", request_id
        ) from exc
    except PluginRuntimeUnavailable as exc:
        raise runtime._runtime_error(exc) from exc
    return result


async def _dispatch_backend_route(
    request: Request,
    *,
    scope: BackendRouteScope,
    route_path: str,
    db: AsyncSession,
    user: User | None = None,
    plugin_id: str | None = None,
) -> Response:
    """Authenticate, authorize, and dispatch a declared plugin backend route."""

    request_id = uuid4()
    resolved = await _resolve_plugin_backend_route(
        scope=scope,
        route_path=route_path,
        method=request.method,
        request_id=request_id,
        plugin_id=plugin_id,
    )
    if user is None:
        user = await get_current_user(request, db)
    owner_id, installation_id = await _authorize_plugin_backend_route(
        db,
        resolved=resolved,
        scope=scope,
        user=user,
        request_id=request_id,
    )
    result = await _execute_plugin_backend_route(
        request,
        resolved=resolved,
        owner_id=owner_id,
        user=user,
        request_id=request_id,
        db=db,
    )
    logger.info(
        "Plugin backend route completed: request_id=%s plugin_id=%s installation_id=%s "
        "route_id=%s scope=%s method=%s user_id=%s status=%s",
        request_id,
        owner_id,
        installation_id,
        resolved.route.id,
        scope.value,
        request.method,
        user.id,
        result.status_code,
    )
    if result.status_code == 204:
        return Response(status_code=204)
    return JSONResponse(
        status_code=result.status_code,
        content=result.body,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.api_route(
    "/{plugin_id}/{route_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def plugin_backend_route(
    plugin_id: str,
    route_path: str,
    request: Request,
    db: AsyncSession = _PLUGIN_DB,
) -> Response:
    """Dispatch one authenticated request within a plugin-owned namespace."""

    return await _dispatch_backend_route(
        request,
        scope=BackendRouteScope.PLUGIN,
        route_path=route_path,
        plugin_id=plugin_id,
        db=db,
    )


@host_router.api_route(
    "/{route_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def plugin_host_backend_route(
    route_path: str,
    request: Request,
    db: AsyncSession = _PLUGIN_DB,
) -> Response:
    """Dispatch a privileged plugin route only after all core routes were considered."""

    return await _dispatch_backend_route(
        request,
        scope=BackendRouteScope.HOST,
        route_path=f"/{route_path}",
        db=db,
    )
