# Application settings

Administrators can manage deployment-wide runtime behaviour from Settings → Application.

## Settings

Secure authentication cookies should be enabled when the browser-facing application is served over HTTPS. Restart the backend after changing this value.

Maximum upload size controls ordinary uploads in MB.

Maximum clip size controls video clips and soundtrack uploads in MB.

Maximum world/modpack size controls world saves and modpack archives in MB.

All numeric limits must be at least 1 MB.

## Persistence

Runtime values are persisted in the deployment settings row. On a new installation, the existing environment values initialise these settings once. After initialisation, administrator changes are not overwritten by environment defaults on every restart.

## Validation

- Open Settings → Application as an administrator.
- Confirm current values load.
- Change each size and verify the new values are saved.
- Enable secure cookies on an HTTPS deployment and restart.
- Confirm the new cookie setting is used after restart.
- Confirm a non-administrator cannot access deployment settings.
