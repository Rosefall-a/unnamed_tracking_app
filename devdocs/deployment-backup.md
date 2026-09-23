# Deployment backup architecture

core/application_backup.py is the shared archive engine used by first-run setup and administrator deployment settings.

The archive records explicit section options and keeps deployment secrets encrypted at rest. The password envelope protects the archive in transit/storage, while the installation Fernet key protects stored secret values after restore.

The Settings → Deployment Backup UI exposes independent controls for application settings, provider credentials, OIDC, SMTP, users/API keys, sessions, and full-installation restore/export. save_to_setup_path writes the encrypted archive to APPLICATION_JSON_PATH.

The setup wizard consumes the same archive format. It previews the archive without mutating the database, then lets the administrator either accept it or populate the multi-page setup flow.

SMTP is a supported deployment-backup section; it is not silently excluded. It is opt-in by default.

Any new deployment field must be assigned to an explicit backup section and must preserve encrypted-at-rest semantics. Add regression coverage for password round trips, wrong passwords, malformed archives, section selection, SMTP/secret preservation, users/API keys, sessions, filesystem discovery, and setup-page population.
