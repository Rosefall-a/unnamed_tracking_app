# Deployment backup

Administrators can create password-protected deployment backups from Settings → Deployment Backup.

The archive uses a password-derived Fernet envelope. Stored application secrets remain encrypted with the installation Fernet key, which is included in protected form so a restore can preserve the encrypted values.

## Export controls

The deployment backup UI can independently include:

- application/deployment settings;
- provider credentials;
- OIDC / SSO configuration;
- SMTP transport and password-reset settings;
- user accounts and API keys;
- active sessions, when users are included;
- full-installation mode, which includes users and active sessions.

The browser download is timestamped. You can optionally save the same encrypted archive to APPLICATION_JSON_PATH (default /data/application.json) for first-run bootstrap.

**SMTP is not excluded.** It is an explicit backup option and is off by default unless selected.

## Setup restore

A fresh installation can discover application.json automatically. The first setup page offers two sources:

1. a manually selected deployment backup file;
2. the detected application.json on the setup filesystem.

The password is verified before the backup is applied. The setup wizard can either accept the imported deployment configuration or populate the subsequent setup pages so the administrator can review it.

The setup wizard is multi-page:

1. choose/import the deployment configuration;
2. create the administrator;
3. optionally configure OIDC;
4. optionally configure SMTP.

## Restore safety

Invalid passwords, malformed archives, unsupported versions, conflicting Fernet key copies, and invalid full-installation data are rejected rather than silently applied.

Optional empty settings are tolerated. Existing encrypted secret values remain encrypted during restore.

## Testing

- Export settings with and without provider credentials.
- Export with OIDC enabled.
- Export with SMTP enabled and verify SMTP fields are restored.
- Export users and API keys.
- Export full installation with active sessions.
- Save an export to the setup path and verify a fresh setup detects it.
- Preview a backup with the correct and incorrect password.
- Choose “populate setup pages” and verify imported OIDC/SMTP values appear in their respective pages.
