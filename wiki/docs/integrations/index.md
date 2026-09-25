# Integrations

Unnamed Tracking App can connect to external services to provide authentication, metadata, game information, and other supplemental data.

## Available integrations

### OIDC / SSO

Use an OpenID Connect provider to let users sign in with an external identity provider.

- Configure one or more OIDC providers.
- Existing users can be matched by email or username.
- Provider groups can optionally grant administrator access.
- Multiple named providers are supported.

See the [OIDC / SSO guide](oidc.md).

### Playnite

The Playnite integration connects the desktop game launcher with Unnamed Tracking App.

It is intended to synchronize game information and collect launcher-related data such as playtime while keeping the web application as the central source of truth.

See the [Playnite guide](playnite.md).

### Metadata providers

External metadata services can be used to enrich games and other media with information such as titles, artwork, descriptions, and related metadata.

Available provider configuration includes services such as:

- SteamGridDB
- RetroAchievements
- GiantBomb
- IGDB
- TMDB
- OMDb
- TVDB
- ScreenScraper
- Xbox

Provider availability and required configuration depend on the type of data being imported or displayed.

See the [Metadata Providers guide](metadata-providers.md).

## General configuration

Most integrations are configured through environment variables or the application's configuration system.

Before enabling an integration:

1. Check the integration's documentation for required credentials or settings.
2. Add the required values to your deployment environment.
3. Restart or redeploy the application when required.
4. Verify the integration from the relevant application feature.

For the complete list of configuration variables, see [Environment Variables](../setup/environment-variables.md).

## Security

Treat API keys, client secrets, and other integration credentials as secrets.

- Do not commit real credentials to the repository.
- Do not put real credentials in example configuration files.
- Use HTTPS when exposing authentication integrations publicly.
- For OIDC behind a reverse proxy, make sure the proxy preserves the original host and scheme so generated callback URLs are correct.
