# Deployment backup

Administrators can create an encrypted deployment backup from Settings → Deployment Backup.

Backups are written to persistent application storage as `application.json` by default. They contain deployment configuration and encrypted provider credentials, but this implementation deliberately excludes SMTP configuration.

The backup password is separate from the application's Fernet key. Keep the password and backup file separate.

## Downloads

Direct browser downloads are disabled by default. Set `ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD=true` in the server environment to expose the Download button.

## Restore during setup

If `application.json` exists in the configured application data directory, the setup page offers a restore flow. Enter the backup password and the application validates the archive before changing the database.
