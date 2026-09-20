# Deployment backup and restore

Deployment backups are the portable, encrypted configuration archive for recreating or cloning an installation. They are separate from Settings → Export / Import, which is for an individual user's library data.

## Export

Administrators use Settings → Deployment Backup.

| Option | Default | Includes |
| --- | --- | --- |
| Application settings | On | Runtime/deployment-wide application settings |
| Provider credentials | On | Provider API identifiers and credentials |
| OIDC / SSO | On | OIDC provider configuration and encrypted client credentials |
| SMTP | Off | SMTP transport and password-reset email settings |
| Users and API keys | Off | User accounts and their API keys |
| Active sessions | Off | Unexpired browser sessions; requires users |
| Full installation | Off | Shortcut for users + active sessions |
| Save to setup path | Off | Writes the archive as application.json at APPLICATION_JSON_PATH |

The downloaded copy is deliberately timestamped, for example: archive-deployment-backup-2026-09-20T06-58-37.json

This lets an administrator keep several exports without overwriting older downloads. When Save to the configured setup path is enabled, the server-side copy is always named application.json. The default path is /data/application.json. Set APPLICATION_JSON_PATH to use another persistent location.

The backup is encrypted with a password supplied at export time. The password must be at least 12 characters and should be stored separately from the archive.

## What is encrypted

The archive contains the installation's persistent Fernet key so encrypted provider/OIDC/SMTP values can remain usable after a restore. Secrets remain encrypted inside the archive rather than being written as plaintext JSON.

A full installation additionally contains user records, password hashes, API keys, and optionally unexpired sessions. A restored password hash is not a plaintext password.

Treat a deployment backup as sensitive even though it is password protected.

## First-run restore

Deployment restore is intentionally a first-run operation. It is available from the /setup wizard and is rejected after a user already exists.

There are two discovery paths:

1. Select a downloaded timestamped backup in the setup wizard.
2. If the configured setup path contains application.json, the wizard detects it automatically and offers Use application.json from the filesystem.

The filesystem copy does not need to have a special download filename. It is discovered from APPLICATION_JSON_PATH.

After the password is entered, setup previews the archive and offers two choices:

### Accept all imported settings

This restores every section represented by the backup's export options. If users are included, their accounts and API keys are restored. If active sessions are included and the browser still has one of those valid session tokens, the restored installation can immediately authenticate that browser and sends it to the home page.

If users are restored but no valid session is available, setup sends the browser to the normal login page rather than creating another administrator.

### Populate the setup pages

This does not immediately commit the deployment settings. Instead, values represented by the backup are used to pre-fill the OIDC and SMTP setup pages. Review those values and finish the setup wizard normally.

This mode is useful when cloning configuration but deliberately creating a new administrator or changing some setup values before committing them.

## Repeatable reset/test workflow

1. Export a deployment backup with the desired sections.
2. Enable Save to the configured setup path.
3. Verify the persistent volume contains application.json.
4. Record the backup password separately.
5. Stop the application and recreate or clear the database as appropriate for the test.
6. Start the application.
7. Open the automatically discovered setup page.
8. Confirm the wizard reports the filesystem application.json.
9. Choose Accept all imported settings for a clone, or Populate the setup pages when you want to review/edit the setup first.
10. Verify login/session behaviour and the imported settings before treating the reset as complete.

Automatic consumption of application.json at application startup is only performed when the database contains no users and APPLICATION_JSON_PASSWORD is configured. This prevents an existing installation from silently re-importing its backup on every restart.

## Backup option dependencies

- Active sessions require users because sessions reference user accounts.
- Full installation enables users and active sessions.
- Provider credentials are independent of OIDC.
- OIDC can be excluded when the destination server should use a different identity provider.
- SMTP is opt-in because mail credentials are often environment-specific.
- Application settings can be excluded when the destination should use its own runtime configuration.
- Unselected sections are not written to the backup payload.

## Security and operational checks

Before moving an archive to another server:

- keep the backup password separate;
- keep the persistent data volume containing application.json private;
- ensure PostgreSQL data is also backed up when a true disaster-recovery copy is required;
- preserve the restored Fernet key and PostgreSQL data together;
- test a restore before relying on the archive for recovery.

A deployment backup is not a complete binary/media backup. It does not replace PostgreSQL backups or backups of the application's media/assets storage.