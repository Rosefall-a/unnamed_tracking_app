"""Compose Plugin Manager routes while retaining established import paths."""

from fastapi import APIRouter
from fastapi import HTTPException as HTTPException
from src.core.auth import get_current_admin as get_current_admin
from src.core.auth import get_current_user as get_current_user
from src.database.session import get_db as get_db
from src.plugin_api.contracts import PluginDependency as PluginDependency
from src.plugin_api.management_auth import get_plugin_manager_admin as get_plugin_manager_admin
from src.plugin_api.management_auth import get_plugin_manager_reader as get_plugin_manager_reader

from .plugin_manager import acquisition, backend, catalogues, contributions, lifecycle, updates
from .plugin_manager.acquisition import (
    _MAX_PLUGIN_PACKAGE_BYTES as _MAX_PLUGIN_PACKAGE_BYTES,
)
from .plugin_manager.acquisition import (
    _MAX_REMOTE_REDIRECTS as _MAX_REMOTE_REDIRECTS,
)
from .plugin_manager.acquisition import (
    _REMOTE_FETCH_TIMEOUT as _REMOTE_FETCH_TIMEOUT,
)
from .plugin_manager.acquisition import (
    _commit_plugin_upload as _commit_plugin_upload,
)
from .plugin_manager.acquisition import (
    _download_remote_file as _download_remote_file,
)
from .plugin_manager.acquisition import (
    _inspect_install_candidate as _inspect_install_candidate,
)
from .plugin_manager.acquisition import (
    _install_plugin_package as _install_plugin_package,
)
from .plugin_manager.acquisition import (
    _install_preview as _install_preview,
)
from .plugin_manager.acquisition import (
    _permission_key as _permission_key,
)
from .plugin_manager.acquisition import (
    _permission_preview as _permission_preview,
)
from .plugin_manager.acquisition import (
    _plan_candidate_dependencies as _plan_candidate_dependencies,
)
from .plugin_manager.acquisition import (
    _plugin_installer as _plugin_installer,
)
from .plugin_manager.acquisition import (
    _plugin_package_verifier as _plugin_package_verifier,
)
from .plugin_manager.acquisition import (
    _resolve_plugin_upload as _resolve_plugin_upload,
)
from .plugin_manager.acquisition import (
    _store_plugin_upload as _store_plugin_upload,
)
from .plugin_manager.acquisition import (
    _validate_catalogue_candidate as _validate_catalogue_candidate,
)
from .plugin_manager.acquisition import (
    _validate_remote_url as _validate_remote_url,
)
from .plugin_manager.acquisition import (
    install_plugin as install_plugin,
)
from .plugin_manager.acquisition import (
    install_plugin_url as install_plugin_url,
)
from .plugin_manager.acquisition import (
    preview_plugin_install as preview_plugin_install,
)
from .plugin_manager.acquisition import (
    preview_plugin_install_url as preview_plugin_install_url,
)
from .plugin_manager.backend import (
    _MAX_PLUGIN_ROUTE_BODY_BYTES as _MAX_PLUGIN_ROUTE_BODY_BYTES,
)
from .plugin_manager.backend import (
    _MAX_PLUGIN_ROUTE_ENVELOPE_BYTES as _MAX_PLUGIN_ROUTE_ENVELOPE_BYTES,
)
from .plugin_manager.backend import (
    _authorize_plugin_backend_route as _authorize_plugin_backend_route,
)
from .plugin_manager.backend import (
    _backend_route_error as _backend_route_error,
)
from .plugin_manager.backend import (
    _backend_route_request as _backend_route_request,
)
from .plugin_manager.backend import (
    _dispatch_backend_route as _dispatch_backend_route,
)
from .plugin_manager.backend import (
    _execute_plugin_backend_route as _execute_plugin_backend_route,
)
from .plugin_manager.backend import (
    _resolve_plugin_backend_route as _resolve_plugin_backend_route,
)
from .plugin_manager.backend import (
    _route_installation as _route_installation,
)
from .plugin_manager.backend import (
    plugin_backend_route as plugin_backend_route,
)
from .plugin_manager.backend import (
    plugin_host_backend_route as plugin_host_backend_route,
)
from .plugin_manager.catalogues import (
    _PLUGIN_CATALOG_URL as _PLUGIN_CATALOG_URL,
)
from .plugin_manager.catalogues import (
    _catalog_entries as _catalog_entries,
)
from .plugin_manager.catalogues import (
    _catalogue_store as _catalogue_store,
)
from .plugin_manager.catalogues import (
    _catalogue_store_for as _catalogue_store_for,
)
from .plugin_manager.catalogues import (
    _check_plugin_update as _check_plugin_update,
)
from .plugin_manager.catalogues import (
    _notify_plugin_update as _notify_plugin_update,
)
from .plugin_manager.catalogues import (
    check_plugin_updates as check_plugin_updates,
)
from .plugin_manager.catalogues import (
    create_plugin_catalogue as create_plugin_catalogue,
)
from .plugin_manager.catalogues import (
    delete_plugin_catalogue as delete_plugin_catalogue,
)
from .plugin_manager.catalogues import (
    list_plugin_catalogues as list_plugin_catalogues,
)
from .plugin_manager.catalogues import (
    plugin_catalog as plugin_catalog,
)
from .plugin_manager.catalogues import (
    update_plugin_catalogue as update_plugin_catalogue,
)
from .plugin_manager.contributions import (
    _DOCUMENT_DATA_ROOT as _DOCUMENT_DATA_ROOT,
)
from .plugin_manager.contributions import (
    _GATEWAY_DISPATCH_TIMEOUT as _GATEWAY_DISPATCH_TIMEOUT,
)
from .plugin_manager.contributions import (
    _GEOIP_UPLOAD_FILE as _GEOIP_UPLOAD_FILE,
)
from .plugin_manager.contributions import (
    _PLUGIN_FRONTEND_CSP as _PLUGIN_FRONTEND_CSP,
)
from .plugin_manager.contributions import (
    _current_browser_session_id as _current_browser_session_id,
)
from .plugin_manager.contributions import (
    _filter_ui_document as _filter_ui_document,
)
from .plugin_manager.contributions import (
    plugin_action as plugin_action,
)
from .plugin_manager.contributions import (
    plugin_document_download as plugin_document_download,
)
from .plugin_manager.contributions import (
    plugin_frontend as plugin_frontend,
)
from .plugin_manager.contributions import (
    plugin_gateway as plugin_gateway,
)
from .plugin_manager.contributions import (
    plugin_geoip_upload as plugin_geoip_upload,
)
from .plugin_manager.contributions import (
    plugin_native_frontend as plugin_native_frontend,
)
from .plugin_manager.contributions import (
    plugin_ui as plugin_ui,
)
from .plugin_manager.contributions import (
    runtime_health as runtime_health,
)
from .plugin_manager.contributions import (
    save_plugin_secret as save_plugin_secret,
)
from .plugin_manager.contributions import (
    save_plugin_settings as save_plugin_settings,
)
from .plugin_manager.lifecycle import (
    _perform_package_operation as _perform_package_operation,
)
from .plugin_manager.lifecycle import (
    _purge_plugin_database as _purge_plugin_database,
)
from .plugin_manager.lifecycle import (
    activate_staged_update as activate_staged_update,
)
from .plugin_manager.lifecycle import (
    create_management_token as create_management_token,
)
from .plugin_manager.lifecycle import (
    delete_package_history as delete_package_history,
)
from .plugin_manager.lifecycle import (
    delete_plugin as delete_plugin,
)
from .plugin_manager.lifecycle import (
    disable_plugin as disable_plugin,
)
from .plugin_manager.lifecycle import (
    enable_plugin as enable_plugin,
)
from .plugin_manager.lifecycle import (
    get_manager_settings as get_manager_settings,
)
from .plugin_manager.lifecycle import (
    grant_plugin_permissions as grant_plugin_permissions,
)
from .plugin_manager.lifecycle import (
    list_plugins as list_plugins,
)
from .plugin_manager.lifecycle import (
    plugin_logs as plugin_logs,
)
from .plugin_manager.lifecycle import (
    preview_plugin_permissions as preview_plugin_permissions,
)
from .plugin_manager.lifecycle import (
    preview_staged_update as preview_staged_update,
)
from .plugin_manager.lifecycle import (
    reinstall_plugin as reinstall_plugin,
)
from .plugin_manager.lifecycle import (
    retry_plugin as retry_plugin,
)
from .plugin_manager.lifecycle import (
    revoke_management_token as revoke_management_token,
)
from .plugin_manager.lifecycle import (
    revoke_plugin_permissions as revoke_plugin_permissions,
)
from .plugin_manager.lifecycle import (
    rollback_plugin as rollback_plugin,
)
from .plugin_manager.lifecycle import (
    run_automatic_plugin_updates as run_automatic_plugin_updates,
)
from .plugin_manager.lifecycle import (
    save_manager_settings as save_manager_settings,
)
from .plugin_manager.lifecycle import (
    set_plugin_auto_update as set_plugin_auto_update,
)
from .plugin_manager.lifecycle import (
    start_plugin as start_plugin,
)
from .plugin_manager.lifecycle import (
    stop_plugin as stop_plugin,
)
from .plugin_manager.models import (
    AutoUpdateIn as AutoUpdateIn,
)
from .plugin_manager.models import (
    CatalogueIcon as CatalogueIcon,
)
from .plugin_manager.models import (
    ManagementTokenIn as ManagementTokenIn,
)
from .plugin_manager.models import (
    ManagerSettingsIn as ManagerSettingsIn,
)
from .plugin_manager.models import (
    PackageOperationIn as PackageOperationIn,
)
from .plugin_manager.models import (
    PluginActionContext as PluginActionContext,
)
from .plugin_manager.models import (
    PluginActionIn as PluginActionIn,
)
from .plugin_manager.models import (
    PluginBackendRouteResponse as PluginBackendRouteResponse,
)
from .plugin_manager.models import (
    PluginCatalogEntry as PluginCatalogEntry,
)
from .plugin_manager.models import (
    PluginCatalogueCreate as PluginCatalogueCreate,
)
from .plugin_manager.models import (
    PluginCatalogueUpdate as PluginCatalogueUpdate,
)
from .plugin_manager.models import (
    PluginGatewayIn as PluginGatewayIn,
)
from .plugin_manager.models import (
    PluginInstallUrl as PluginInstallUrl,
)
from .plugin_manager.models import (
    PluginSettingsIn as PluginSettingsIn,
)
from .plugin_manager.runtime import (
    _PLUGIN_ADMIN as _PLUGIN_ADMIN,
)
from .plugin_manager.runtime import (
    _PLUGIN_DB as _PLUGIN_DB,
)
from .plugin_manager.runtime import (
    _client as _client,
)
from .plugin_manager.runtime import (
    _installed_plugins as _installed_plugins,
)
from .plugin_manager.runtime import (
    _live_plugin as _live_plugin,
)
from .plugin_manager.runtime import (
    _plugin_and_capabilities as _plugin_and_capabilities,
)
from .plugin_manager.runtime import (
    _private_plugin_response as _private_plugin_response,
)
from .plugin_manager.runtime import (
    _runtime_error as _runtime_error,
)
from .plugin_manager.runtime import (
    _runtime_errors as _runtime_errors,
)
from .plugin_manager.runtime import (
    _runtime_request_error as _runtime_request_error,
)
from .plugin_manager.updates import (
    _update_context as _update_context,
)
from .plugin_manager.updates import (
    _update_plugin_package as _update_plugin_package,
)
from .plugin_manager.updates import (
    _update_preview as _update_preview,
)
from .plugin_manager.updates import (
    plugin_changelog as plugin_changelog,
)
from .plugin_manager.updates import (
    preview_plugin_update as preview_plugin_update,
)
from .plugin_manager.updates import (
    preview_plugin_update_url as preview_plugin_update_url,
)
from .plugin_manager.updates import (
    update_plugin as update_plugin,
)
from .plugin_manager.updates import (
    update_plugin_url as update_plugin_url,
)

router = APIRouter()
for module in (acquisition, catalogues, lifecycle, updates, contributions, backend):
    router.include_router(module.router)
host_router = backend.host_router


# Retain established imports while their implementations have separate owners.
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
    "_runtime_errors",
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
]
