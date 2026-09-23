# Setup

The first-run setup wizard is a multi-page flow.

## First page: deployment import

The first page is the deployment choice page. It allows an administrator to:

- select an encrypted deployment backup file;
- enter its backup password;
- review the backup before applying it;
- use an automatically detected application.json from the configured setup path;
- choose whether to accept the imported deployment configuration or populate the setup pages from it.

This page appears before the administrator account page.

## Setup pages

After the deployment choice:

1. **Account** creates the first administrator.
2. **OIDC** is available when SSO is selected and exposes the provider setup fields.
3. **SMTP** is available when email transport is selected.

Imported OIDC and SMTP settings are populated into the corresponding pages rather than being silently discarded.

## Environment control

SETUP_MODE controls whether the interactive setup UI is available. Environment-controlled values remain authoritative over browser-submitted values.

PAGE__OBJECT__FIELD namespaces are used for declarative setup configuration. Secrets are never returned as plaintext environment metadata.

## Backup

The setup flow uses the same encrypted deployment backup format as Settings → Deployment Backup. APPLICATION_JSON_PATH defaults to /data/application.json.

A backup can include application settings, provider credentials, OIDC, SMTP, users/API keys, and active sessions according to the selected export options.
