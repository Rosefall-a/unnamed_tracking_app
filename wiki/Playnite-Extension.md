# Playnite Extension

The companion repository is `Rosefall-a/UnnamedTrackingPlaynite`.

It is a Playnite 10 generic plugin for synchronizing a Playnite library with an Unnamed Tracking server.

## Connection

The extension settings require:

1. The Unnamed Tracking base URL.
2. A user API key beginning with `utk_`.

In Playnite:

1. Install the extension package.
2. Open **Add-ons → Extension settings → Unnamed Tracking**.
3. Enter the server URL.
4. Enter the user API key.
5. Use **Test connection**.
6. Use **Upload Playnite Library** for the initial synchronization.

The API key is stored by Playnite with extension settings. Treat the Playnite profile as sensitive configuration.

## Library synchronization

The extension can:

- synchronize the complete Playnite library
- synchronize selected games
- preview changes before uploading
- create remote games
- update existing remote games
- upload cover/banner artwork
- ignore games carrying a configured ignore tag
- synchronize on Playnite startup
- update already-linked games when a game stops
- cancel a manual synchronization

The default ignore tag is `trackingapp_ignore`.

## Game identity

The extension sends `playnite_guid` and a generated `folder_location`.

Existing games are matched first by generated folder location and then by Playnite GUID. This is intended to prevent renaming a Playnite game from creating a second remote game.

## Save synchronization

Save synchronization is local to the extension's configuration and keyed by Playnite game GUID.

It supports:

- multiple local save folders/files
- upload on demand
- download of the latest cloud save
- automatic download on game start
- automatic upload on game stop
- environment-variable expansion such as `%USERPROFILE%`
- timestamped local backups before cloud downloads overwrite local files

The save archive API uses the authenticated API key directly.

## API contract

The extension currently relies on authenticated endpoints including:

- `GET /api/game/list`
- `POST /api/game/create`
- `PATCH /api/game/update/{game_id}`
- `POST /api/game/{game_id}/assets/{asset_kind}`
- save archive endpoints under `/api/game/{game_id}/archives/`

The extension's own repository should remain the authoritative source for detailed Playnite implementation, packaging and release instructions.

## Important distinction

The embedded sidebar can open the configured Unnamed Tracking web UI, but the API key is not placed in the page URL or browser storage. The normal web UI uses a browser session, so the embedded UI may still require a normal web login even though save/library API operations use the extension's API key.

## Known integration issue

The application repository has an open issue tracking duplicate-create robustness for Playnite synchronization (#184). The extension repository has also had separate update-endpoint work. These should not be conflated: an API-side duplicate-create race/identity problem is different from a client using the wrong endpoint.
