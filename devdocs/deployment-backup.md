# Deployment backup architecture

`core/application_backup.py` is the single archive engine used by both the setup flow and the administrator Settings page.

## Archive lifecycle

1. `build_application_backup()` reads the deployment models.
2. SMTP fields are explicitly filtered out.
3. The installation Fernet key copies are included so encrypted values remain decryptable after restore.
4. `encrypt_application_backup()` wraps the JSON in a password-derived Fernet envelope.
5. The admin route writes the encrypted bytes to `application_backup_path()`.
6. Setup can preview or restore the same file before normal authentication exists.

## Persistent location

The default path is `<APP_DATA_DIR>/application.json`. A future deployment may override the path through `APPLICATION_JSON_PATH` without changing the backup format.

## Adding a new secret

Add its model field to the secret-field list in `application_backup.py`, ensure export preserves the encrypted-at-rest representation, and add a restore test. Never put a plaintext secret into a backup merely because it is convenient.

## Adding a new setup page

Register its namespace with `SetupConfiguration`, expose its environment tree to the setup status endpoint, and consume overrides at the page's save boundary. Do not add direct environment parsing to the backup route.

## Security boundary

The password protects the archive in transit/storage; the persistent Fernet key protects application secrets at rest. Both are required for a correct restore. Direct downloads therefore remain opt-in.
