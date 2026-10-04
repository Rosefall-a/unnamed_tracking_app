# Pelican plugin system audit

Sources: `app/Services/Helpers/PluginService.php`, `app/Models/Plugin.php`, the `p:plugin:*` commands, the Filament panel providers, and the official catalogue `pelican-dev/plugins` (`announcements, billing, generic-oidc-providers, mclogs-uploader, minecraft-modrinth, player-counter, register, rust-umod, subdomains, tickets, user-creatable-servers, …`).

## What a Pelican plugin is

A directory under `plugins/<id>/` with a `plugin.json` (id, namespace, class, `panels`, `panel_version`, `composer_packages`). When loaded, the Panel:

* adds the plugin's `src/` to the Composer autoloader and loads `config/<id>.php`;
* registers its **Laravel service providers**, so it can bind anything in the container, listen to any event, and add routes;
* registers its **artisan commands**, **database migrations**, **views** and **translations**;
* lets it contribute **Filament resources, pages and widgets** to the `admin`, `app` and `server` panels;
* installs its **Composer packages** into the Panel's own vendor tree (`composer require` at install time);
* can register extra subuser permissions (`Subuser::registerCustomPermissions`), Application-key resources (`ApiKey::registerCustomResourceName`), role permissions and webhook event names (`server:webhook.events`).

There is **no sandbox**. Plugin code runs in-process with the Panel: full database access, the encrypted Wings daemon tokens, and the ability to call any Wings endpoint as the Panel. Installing one is equivalent to modifying the Panel.

## Extension points relevant to Unnamed Tracking

| Need | What a Pelican plugin could do | Evidence |
| --- | --- | --- |
| Expose new Client API endpoints | `routes/api-client.php` under the same auth and server middleware. `player-counter` adds `GET /api/client/servers/{id}/query` and `/query/players` | Source |
| Game queries (player count and names) | `player-counter` runs Minecraft Java ping/query, Bedrock, Source, GoldSource, Palworld and CitizenFX queries **from the Panel host** | Source |
| Pull a world from UT on the LAN | Panel-side code has no SSRF block (unlike Wings `files/pull`). It could download from UT and push to Wings with the daemon token | Inferred from source; not built |
| Mark servers as UT-managed, custom UI | Filament widgets on the server panel | Source |
| Push events to UT | Model and activity events → HTTP (webhooks already do this without a plugin) | Source |
| Console, readiness, player join/leave | **Not available to the Panel.** Console output never reaches it; the Panel only proxies JWTs for the browser's direct websocket to Wings | Source + E02 |

## Is a companion plugin necessary?

**Not for Run, Track, Visualise or Preserve as designed** ([architecture](architecture.md)):

* Run and Capture work with the stock Client API and a least-privilege subuser key (E03, E04c, E06, E12).
* Real-time status and player events need the Wings websocket, which a Panel plugin can't provide either.
* LAN world transfer is solved by the UT host bridge pushing to the signed Wings upload URL (E03, E12). That avoids `files/pull` and any Panel-side download.

It would be **useful but optional** in two places, both after milestone 1:

1. **Game-query presence** (`player-counter`) as a second, polling-based player source for games whose console doesn't log joins. It needs no UT-specific code: install the official plugin and call its JSON route through the bridge.
2. **Hosting admin conveniences** if server creation is added (D2 defers it): pre-approved eggs and nodes for UT-created servers, enforced server-side instead of by an admin-wide Application key.

## Risks of building one

* It must be trusted as Panel code, kept compatible with Pelican's beta cadence (`panel_version`), and installed by a Pelican admin. That is a different person than the UT user in many homelabs.
* Any credential it holds for UT (to pull worlds) becomes a Panel-side secret with full Panel blast radius.

**Recommendation:** no companion plugin in milestones 1–3. Treat `player-counter` as an optional, detected enhancement. Revisit a purpose-built plugin only if server creation needs server-side policy enforcement.
