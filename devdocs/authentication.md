# Authentication architecture

core/auth.py creates random browser credentials and stores only their SHA-256 hashes in UserSession.

session_cookie_name derives an installation-specific cookie namespace from the persisted Fernet key. The authentication reader accepts the current namespace, the legacy session cookie, and restored session namespaces. The database hash remains the authoritative credential check.

revoke_session deletes by token hash and commits the transaction. Logout is deliberately idempotent.

ensure_primary_user and user administration treat primary-account environment values defensively. Do not compare an empty primary username or email directly against users.

API keys return the raw credential once, a display prefix, and a hash for persistence. Authentication checks the hash and requires an active, non-revoked key.

New credential types should generate opaque credentials, persist only a one-way derivative where practical, check active/revoked state explicitly, make revocation idempotent, avoid logging credential material, and include lifecycle regression coverage.
