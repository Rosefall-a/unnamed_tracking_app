# Deployment backup architecture

core/application_backup.py is the shared archive engine used by setup and administrator deployment settings.

Export builds a structured archive, preserves encrypted-at-rest secret representations, and wraps the archive in a password-derived encryption envelope. The persistent application Fernet key is included only in the protected form required to restore encrypted values.

The setup route can preview or restore the same archive before normal authentication exists. The administrator export route writes a persistent setup-path copy when requested.

The setup-path copy is application.json. Browser downloads are timestamped and direct deployment-secret downloads are opt-in.

## Restore boundary

Restore is intended for an empty installation. The setup route validates the archive before changing the database and reports database conflicts rather than silently overwriting unrelated state.

When users and sessions are restored, authentication accepts the restored session namespace. This is why authentication and backup documentation must be kept consistent.

## Extending the archive

Add new deployment fields to the archive schema deliberately. Secret fields must remain encrypted at rest and require a restore test. Do not add plaintext credentials for convenience.

Any new setup namespace should be registered with SetupConfiguration and documented separately from the archive engine.

## Testing

Cover password round trips, wrong passwords, malformed archives, empty optional settings, encrypted secret preservation, users/API keys, optional sessions, filesystem discovery, preview, and restore conflict handling.
