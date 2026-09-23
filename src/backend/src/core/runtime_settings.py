"""Apply persisted application settings to the live process configuration."""

from typing import TYPE_CHECKING

from src.core.config import settings

if TYPE_CHECKING:
    from src.database.models.app_integration_settings import AppIntegrationSettings


def apply_runtime_settings(app_settings: "AppIntegrationSettings") -> None:
    """Apply the admin-controlled runtime values used by the application."""
    settings.AUTH_COOKIE_SECURE = app_settings.auth_cookie_secure
    settings.MAX_UPLOAD_SIZE_MB = app_settings.max_upload_size_mb
    settings.MAX_CLIP_SIZE_MB = app_settings.max_clip_size_mb
    settings.MAX_WORLD_SAVE_SIZE_MB = app_settings.max_world_save_size_mb
