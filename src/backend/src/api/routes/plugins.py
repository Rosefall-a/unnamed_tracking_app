"""Compose Plugin Manager routes while retaining established import paths."""

from fastapi import APIRouter, HTTPException

from src.core.auth import get_current_admin, get_current_user
from src.database.session import get_db
from src.plugin_api.contracts import PluginDependency
from src.plugin_api.management_auth import get_plugin_manager_admin, get_plugin_manager_reader

from .plugin_manager import acquisition, backend, catalogues, contributions, lifecycle, updates
from .plugin_manager.acquisition import (
    _MAX_PLUGIN_PACKAGE_BYTES,
    _MAX_REMOTE_REDIRECTS,
    _REMOTE_FETCH_TIMEOUT,
    _install_plugin_package,
    _plan_candidate_dependencies,
    _resolve_plugin_upload,
    install_plugin,
    install_plugin_url,
    preview_plugin_install,
    preview_plugin_install_url,
)
from .plugin_manager.acquisition import acquisition_source as _acquisition_source
from .plugin_manager.acquisition import commit_plugin_upload as _commit_plugin_upload
from .plugin_manager.acquisition import download_remote_file as _download_remote_file
from .plugin_manager.acquisition import inspect_install_candidate as _inspect_install_candidate
from .plugin_manager.acquisition import install_preview as _install_preview
from .plugin_manager.acquisition import permission_key as _permission_key
from .plugin_manager.acquisition import permission_preview as _permission_preview
from .plugin_manager.acquisition import plugin_installer as _plugin_installer
from .plugin_manager.acquisition import plugin_package_verifier as _plugin_package_verifier
from .plugin_manager.acquisition import store_plugin_upload as _store_plugin_upload
from .plugin_manager.acquisition import (
    validate_catalogue_candidate as _validate_catalogue_candidate,
)
from .plugin_manager.acquisition import validate_remote_url as _validate_remote_url
from .plugin_manager.backend import (
    _MAX_PLUGIN_ROUTE_BODY_BYTES,
    _MAX_PLUGIN_ROUTE_ENVELOPE_BYTES,
    _authorize_plugin_backend_route,
    _backend_route_error,
    _backend_route_request,
    _dispatch_backend_route,
    _execute_plugin_backend_route,
    _resolve_plugin_backend_route,
    _route_installation,
    plugin_backend_route,
    plugin_host_backend_route,
)
from .plugin_manager.catalogues import (
    _PLUGIN_CATALOG_URL,
    _catalog_entries,
    _catalogue_store_for,
    check_plugin_updates,
    create_plugin_catalogue,
    delete_plugin_catalogue,
    list_plugin_catalogues,
    plugin_catalog,
    update_plugin_catalogue,
)
from .plugin_manager.catalogues import catalogue_store as _catalogue_store
from .plugin_manager.catalogues import check_plugin_update as _check_plugin_update
from .plugin_manager.catalogues import notify_plugin_update as _notify_plugin_update
from .plugin_manager.contributions import (
    _DOCUMENT_DATA_ROOT,
    _GATEWAY_DISPATCH_TIMEOUT,
    _GEOIP_UPLOAD_FILE,
    _PLUGIN_FRONTEND_CSP,
    _filter_ui_document,
    plugin_action,
    plugin_document_download,
    plugin_frontend,
    plugin_gateway,
    plugin_geoip_upload,
    plugin_native_frontend,
    plugin_ui,
    runtime_health,
    save_plugin_secret,
    save_plugin_settings,
)
from .plugin_manager.contributions import current_browser_session_id as _current_browser_session_id
from .plugin_manager.lifecycle import (
    _perform_package_operation,
    _purge_plugin_database,
    activate_staged_update,
    create_management_token,
    delete_package_history,
    delete_plugin,
    disable_plugin,
    enable_plugin,
    get_manager_settings,
    grant_plugin_permissions,
    list_plugins,
    plugin_logs,
    preview_plugin_permissions,
    preview_staged_update,
    reinstall_plugin,
    retry_plugin,
    revoke_management_token,
    revoke_plugin_permissions,
    rollback_plugin,
    run_automatic_plugin_updates,
    save_manager_settings,
    set_plugin_auto_update,
    start_plugin,
    stop_plugin,
)
from .plugin_manager.models import (
    AutoUpdateIn,
    CatalogueIcon,
    ManagementTokenIn,
    ManagerSettingsIn,
    PackageOperationIn,
    PluginActionContext,
    PluginActionIn,
    PluginBackendRouteResponse,
    PluginCatalogEntry,
    PluginCatalogRelease,
    PluginCatalogueCreate,
    PluginCatalogueUpdate,
    PluginGatewayIn,
    PluginInstallUrl,
    PluginSettingsIn,
)
from .plugin_manager.runtime import PLUGIN_ADMIN as _PLUGIN_ADMIN
from .plugin_manager.runtime import PLUGIN_DB as _PLUGIN_DB
from .plugin_manager.runtime import client as _client
from .plugin_manager.runtime import installed_plugins as _installed_plugins
from .plugin_manager.runtime import live_plugin as _live_plugin
from .plugin_manager.runtime import plugin_and_capabilities as _plugin_and_capabilities
from .plugin_manager.runtime import private_plugin_response as _private_plugin_response
from .plugin_manager.runtime import runtime_error as _runtime_error
from .plugin_manager.runtime import runtime_request_error as _runtime_request_error
from .plugin_manager.updates import (
    _update_plugin_package,
    plugin_changelog,
    preview_plugin_update,
    preview_plugin_update_url,
    update_plugin,
    update_plugin_url,
)
from .plugin_manager.updates import update_context as _update_context
from .plugin_manager.updates import update_preview as _update_preview

router = APIRouter()
for module in (acquisition, catalogues, lifecycle, updates, contributions, backend):
    router.include_router(module.router)
host_router = backend.host_router


# Compatibility exports retained for callers of the original route module.
__all__ = [
    "AutoUpdateIn",
    "CatalogueIcon",
    "HTTPException",
    "ManagementTokenIn",
    "ManagerSettingsIn",
    "PackageOperationIn",
    "PluginActionContext",
    "PluginActionIn",
    "PluginBackendRouteResponse",
    "PluginCatalogEntry",
    "PluginCatalogRelease",
    "PluginCatalogueCreate",
    "PluginCatalogueUpdate",
    "PluginDependency",
    "PluginGatewayIn",
    "PluginInstallUrl",
    "PluginSettingsIn",
    "_DOCUMENT_DATA_ROOT",
    "_GATEWAY_DISPATCH_TIMEOUT",
    "_GEOIP_UPLOAD_FILE",
    "_MAX_PLUGIN_PACKAGE_BYTES",
    "_MAX_PLUGIN_ROUTE_BODY_BYTES",
    "_MAX_PLUGIN_ROUTE_ENVELOPE_BYTES",
    "_MAX_REMOTE_REDIRECTS",
    "_PLUGIN_ADMIN",
    "_PLUGIN_CATALOG_URL",
    "_PLUGIN_DB",
    "_PLUGIN_FRONTEND_CSP",
    "_REMOTE_FETCH_TIMEOUT",
    "_acquisition_source",
    "_authorize_plugin_backend_route",
    "_backend_route_error",
    "_backend_route_request",
    "_catalog_entries",
    "_catalogue_store",
    "_catalogue_store_for",
    "_check_plugin_update",
    "_client",
    "_commit_plugin_upload",
    "_current_browser_session_id",
    "_dispatch_backend_route",
    "_download_remote_file",
    "_execute_plugin_backend_route",
    "_filter_ui_document",
    "_inspect_install_candidate",
    "_install_plugin_package",
    "_install_preview",
    "_installed_plugins",
    "_live_plugin",
    "_notify_plugin_update",
    "_perform_package_operation",
    "_permission_key",
    "_permission_preview",
    "_plan_candidate_dependencies",
    "_plugin_and_capabilities",
    "_plugin_installer",
    "_plugin_package_verifier",
    "_private_plugin_response",
    "_purge_plugin_database",
    "_resolve_plugin_backend_route",
    "_resolve_plugin_upload",
    "_route_installation",
    "_runtime_error",
    "_runtime_request_error",
    "_store_plugin_upload",
    "_update_context",
    "_update_plugin_package",
    "_update_preview",
    "_validate_catalogue_candidate",
    "_validate_remote_url",
    "activate_staged_update",
    "check_plugin_updates",
    "create_management_token",
    "create_plugin_catalogue",
    "delete_package_history",
    "delete_plugin",
    "delete_plugin_catalogue",
    "disable_plugin",
    "enable_plugin",
    "get_current_admin",
    "get_current_user",
    "get_db",
    "get_manager_settings",
    "get_plugin_manager_admin",
    "get_plugin_manager_reader",
    "grant_plugin_permissions",
    "install_plugin",
    "install_plugin_url",
    "list_plugin_catalogues",
    "list_plugins",
    "plugin_action",
    "plugin_backend_route",
    "plugin_catalog",
    "plugin_changelog",
    "plugin_document_download",
    "plugin_frontend",
    "plugin_gateway",
    "plugin_geoip_upload",
    "plugin_host_backend_route",
    "plugin_logs",
    "plugin_native_frontend",
    "plugin_ui",
    "preview_plugin_install",
    "preview_plugin_install_url",
    "preview_plugin_permissions",
    "preview_plugin_update",
    "preview_plugin_update_url",
    "preview_staged_update",
    "reinstall_plugin",
    "retry_plugin",
    "revoke_management_token",
    "revoke_plugin_permissions",
    "rollback_plugin",
    "run_automatic_plugin_updates",
    "runtime_health",
    "save_manager_settings",
    "save_plugin_secret",
    "save_plugin_settings",
    "set_plugin_auto_update",
    "start_plugin",
    "stop_plugin",
    "update_plugin",
    "update_plugin_catalogue",
    "update_plugin_url",
    "host_router",
    "router",
]
