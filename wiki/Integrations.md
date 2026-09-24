# Integrations

Unnamed Tracking has two broad integration categories:

1. Deployment-wide provider credentials.
2. Per-user credentials and linked libraries.

## Metadata providers

Current deployment-level environment fallbacks include:

- IGDB
- TMDB
- OMDb
- TheTVDB
- SteamGridDB
- RetroAchievements
- GiantBomb
- ScreenScraper

The exact provider capabilities vary by media type.

The Settings UI can store deployment-wide credentials in the database. Secrets are encrypted at rest.

## Credential precedence

For providers represented by the deployment integration system, the effective value is selected from the most specific available source.

Typical order:

1. User credential, where the provider supports user credentials.
2. Deployment-wide database credential.
3. Environment fallback.

IGDB deployment credentials are deployment-wide. Xbox client credentials can also be deployment-wide, with user OAuth data remaining user-specific.

## OIDC

OIDC configuration is deployment-level and can contain multiple named providers in the database. Environment variables remain for backwards compatibility/default-provider bootstrap.

## SMTP

SMTP is a deployment-level application setting rather than one of the current Pydantic `.env` settings. It is therefore not part of the environment-variable table simply because it is configurable.

The same principle applies to many Settings UI values: the wiki should not incorrectly describe every database setting as an environment variable.

## Provider configuration recommendations

For new installations, use Settings → Server Integrations where the feature exists. This keeps secrets encrypted in PostgreSQL and makes configuration visible to administrators without exposing the secret value back to the browser.

Environment fallbacks remain useful for automated/container deployments and backwards compatibility.
