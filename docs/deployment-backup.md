# Deployment backup

Administrators can create password-protected deployment backups from Settings → Deployment Backup.

The archive is encrypted with a password-derived Fernet envelope. Application secrets remain protected by the installation Fernet key. Keep the backup file and its password separate.

## Export

A deployment-settings export contains deployment-wide application/provider configuration and the encrypted secret values required to restore that configuration.

An optional full-installation export also includes user accounts and their API keys. Active sessions can be included only when users are included.

The normal browser download uses a timestamped filename. An optional persistent setup-path copy is stored as application.json at APPLICATION_JSON_PATH, which defaults to /data/application.json.

Direct browser downloads of deployment-secret archives are disabled unless ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD=true.

## Setup restore

A fresh installation can discover application.json automatically. The setup page can review the backup before changing the installation.

The restore flow validates the password and archive before applying it. If a backup contains settings only, the administrator continues by creating a new administrator. A full installation can restore users and, when selected, sessions.

The setup flow can also accept a manually uploaded backup file.

## Restore safety

A restore is intended for an empty installation during setup. Invalid passwords, malformed archives, incompatible data, and database conflicts are rejected without silently applying partial settings.

Optional settings with empty values are tolerated. Existing encrypted secret representations are preserved rather than accidentally converted to plaintext.

## Repeatable deployment testing

1. Export a backup and save it to the persistent setup path.
2. Keep the backup password separately.
3. Recreate an empty database while retaining application data.
4. Start the application.
5. Confirm the setup wizard discovers application.json.
6. Review the backup and accept it.
7. Verify deployment settings and encrypted credentials.
8. For a full installation, verify users, API keys, and selected sessions.

## Security

Do not expose deployment-secret downloads unless there is a deliberate operational reason. Losing the persistent Fernet key prevents encrypted application secrets from being decrypted.
