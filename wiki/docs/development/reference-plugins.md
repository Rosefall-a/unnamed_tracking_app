# Reference plugins

The independent [`unnamed_tracking_app_plugins`](https://github.com/Rosefall-a/unnamed_tracking_app_plugins) repository contains packages that consume the public boundary without importing application source.

## Scoped Document Viewer

`example.scoped-document-viewer` contributes a sandboxed Documents sidebar page and requests only `documents.read`. It lists opaque document DTOs and renders browser-native PDF or plain text. Ownership, path confinement, MIME checks, UTF-8 validation, active-content rejection, and the 5 MiB limit remain in the host.

## Self-Service Session Manager

`example.self-service-session-manager` contributes an Account sessions page. It requests `sessions.read` and `sessions.revoke` separately. The host performs confirmation before revocation and scopes both operations to the signed-in user. The plugin never receives credential material.

## Help Button

`example.help-button` demonstrates plugin-owned routes/navigation, the `app.global` extension slot, the Home Hub `home.replace` slot, dialogs, and explicitly declared external navigation.

## Jellyfin Media Sync

`example.jellyfin-media-sync` demonstrates plugin settings, write-only plugin secrets, Jellyfin HTTP API access, media read/import, background synchronization, and event-driven update polling.

## Focused references and useful demos

The current repository also maintains UI/API (declarative pages, settings and actions), Playtime Report (scoped library reports), Recently Played Notifier (notifications), Metadata Curator (metadata search and settings), and UI Playground (sandboxed Vue pages and the bridge). These are maintained examples, not retired sources. Historical lifecycle/events/advanced packages remain immutable release records and are separate from these current sources.

### External Discord Delivery Provider

`example.discord-delivery-provider` demonstrates core-coordinated external notification delivery and write-only secrets through the narrowly scoped runtime sender. It does not receive arbitrary networking authority.

## Official features and previews

`official.jellyfin-media-sync` is a separately identified official preview derived from the Jellyfin demonstration. `official.pwa` provides host-owned install metadata and a public-asset-only service worker. Both start at 0.0.1 and remain outside signed publication until their protected official signing identity is reviewed. Development validation includes these previews; it does not imply a production release.

## Build and install

Run `python tools/build_packages.py`, then verify and validate the resulting `.utp` files with the repository tools. Development artifacts are unsigned and trigger the untrusted-package consent warning. Release CI uses the reviewed private signing identity; private keys are never stored in either repository.

Install through the normal Plugin Manager preview/consent flow. A reference page disappears when its plugin is disabled or removed, and requests fail immediately when the relevant grant is revoked.


## Current official reference plugins

Alongside the focused examples above, the plugin repository maintains four substantial feature demonstrations:

- **Help Button (Totally Not Helpful)** — demonstrates plugin-owned routes/navigation, the `app.global` extension slot, the Home Hub `home.replace` slot, and explicitly declared external navigation.
- **Jellyfin Media Sync** — demonstrates plugin settings, write-only plugin secrets, Jellyfin HTTP API access, media read/import, background synchronization, and cursor-based `game.updated` / `media.added` event polling.
- **Self-Service Session Manager** — implements scoped own/admin sessions and privileged native Settings/maps.
- **Scoped Document Viewer** — implements scoped document APIs and sandboxed PDF/text/Office presentation.

### Full API warning

The `api.full` capability is intentionally separate from all scoped capabilities and is never granted implicitly. **Full API access allows plugins to read and modify all user data. Only enable this for plugins you trust.** Prefer scoped capabilities whenever possible.
