# Administration

Administrators manage users, deployment settings, provider credentials, scheduled jobs, imports/exports, backups, and plugins from Settings.

## Settings sections

Administration separates **Users**, **Single sign-on**, **Server integrations**, **Limits**, **Developer tools**, **App branding**, **Plugins**, **Background tasks** and **Storage & usage**. Each section has its own Settings deep link and consistent page heading. Older `section=admin&tab=...` links resolve to the corresponding section. These server controls remain administrator-only.

## Upload limits

Open **Administration → Limits** to change all four environment-backed caps: images/general files (`MAX_UPLOAD_SIZE_MB`), save archives (`MAX_SAVE_ARCHIVE_SIZE_MB`), video clips and soundtracks (`MAX_CLIP_SIZE_MB`), and world saves/modpacks (`MAX_WORLD_SAVE_SIZE_MB`). Values are whole megabytes, saved for the deployment and enforced on new uploads immediately. Existing files are retained. **Reset all to server defaults** clears the overrides and uses the current environment configuration.

The nullable migration preserves existing provider credentials, branding and the earlier general-upload override. Unconfigured limits keep their environment values. This page edits application upload caps; plugin package verification and per-plugin runtime quotas retain their existing security boundaries.

## Operational checklist

1. Configure HTTPS, secure cookies, a unique Fernet `SECRET_KEY`, database credentials, and a unique plugin-runtime token.
2. Create only the users and API keys that are needed.
3. Configure metadata/OIDC credentials through deployment settings or environment variables; environment-managed values remain authoritative.
4. Review scheduled-job intervals and backup status.
5. Install plugins only from a reviewed package, inspect every requested permission, and keep untrusted-package confirmation enabled.
6. Monitor application logs and per-plugin structured diagnostics without copying secrets into support reports.

See [Users](users.md), [App branding](branding.md), [Scheduled tasks](tasks.md), [Plugin administration](plugins.md), and [Startup and troubleshooting](../deployment/startup-and-troubleshooting.md).
