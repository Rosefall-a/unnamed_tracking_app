# Authentication and sessions

Password login creates an opaque random browser session. Only a SHA-256 hash of the session token is stored in PostgreSQL.

Logout is idempotent: the matching database session is revoked before the browser cookie is cleared, and repeating logout remains successful.

Session cookies are namespaced from the installation's persistent Fernet key. This prevents two self-hosted installations on the same hostname but different ports from accidentally sharing a cookie name. Legacy session cookies and restored session namespaces remain readable for compatibility.

API keys are random opaque credentials. Only the hash and a short prefix are stored; the complete key is returned only when it is created.

Administrators can promote or demote normal users. A configured primary account cannot be demoted or deleted, and an administrator cannot remove their own admin access. Empty or unset primary-account environment variables do not accidentally match every user.

Changing a password requires the current password.

## Manual validation

- Log in with username and email.
- Refresh and confirm the session survives.
- Log out and confirm the old session no longer authenticates.
- Repeat logout.
- Run two local installations on different ports and confirm their cookies do not collide.
- Restore an installation containing sessions and verify a valid restored session can authenticate.
- Create and revoke an API key.
- Promote and demote a normal user.
- Verify the primary account cannot be demoted or deleted.
- Verify an administrator cannot remove their own admin access.
- Change a password and confirm the old password stops working.
