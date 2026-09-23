# Application runtime settings architecture

AppIntegrationSettings persists auth_cookie_secure, max_upload_size_mb, max_clip_size_mb, max_world_save_size_mb, and runtime_settings_initialized.

core/runtime_settings.py is the single boundary that copies persisted values into the live process-level configuration.

Startup obtains the singleton row. If runtime_settings_initialized is false, environment values seed the row once. The row is then committed and apply_runtime_settings copies the persisted values into the live settings object. This prevents administrator changes from being overwritten by environment defaults on every restart.

The deployment settings API validates numeric limits and applies saved values immediately. Cookie-security changes require a restart because middleware is constructed during application startup.

The runtime migration adds only these runtime columns to app_integration_settings. Keep future process-wide settings in the same deployment row and document whether they require a restart.
