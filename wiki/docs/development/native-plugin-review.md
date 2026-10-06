# Native plugin layout review

The current unsigned Jellyfin and theme packages were installed through the
public package review and consent flow in an isolated test server. The native
Document Browser settings came from the validated distribution artifact.

Loaded Jellyfin server and account settings and Document Browser controls were
checked at 320, 390, 1440 and 1920 pixels in light and dark modes. The checks wait
for configuration to load, verify administrator access, and reject horizontal
overflow. Official Jellyfin entries are direct items under **Server management**,
**Account**, and the **Media** sidebar heading.

![Loaded Jellyfin server settings](../assets/ui-redevelopment/jellyfin-admin-loaded-1440-light.png)

![Jellyfin accounts on a phone](../assets/ui-redevelopment/jellyfin-accounts-loaded-390-dark.png)

![Loaded Document Browser settings](../assets/ui-redevelopment/document-browser-settings-loaded-1440-light.png)

![Document Browser settings on a phone](../assets/ui-redevelopment/document-browser-settings-loaded-390-dark.png)

Purple Blocks demonstrates the granted global stylesheet capability: it squares
the sidebar, account controls, settings navigation, phone tabs and plugin forms.
Switching to Blue Hour releases its shape overrides.

![Purple Blocks across the desktop shell and native plugin](../assets/ui-redevelopment/purple-blocks-native-shell-1440-light.png)

![Purple Blocks across the phone shell and native plugin](../assets/ui-redevelopment/purple-blocks-native-shell-390-dark.png)

The live Jellyfin check exercised connection, discovery and username/password
sign-in without a manually supplied UUID. Synchronization was disabled, the
media-write permission was denied, and the processed-media count stayed zero.
Test credentials were removed from plugin storage. The public screenshots use
an empty disposable configuration and contain no live server information.

## Permission lifecycle and diagnostics

The installed native test fixture also exercises permission presentation at 390
and 1440 pixels. Active and denied access fold independently, one logical scope
appears once, and icons use the host risk colours. Exact user/device scopes remain
separate. The backend tests cover repeated rejection/reinstatement, historical
duplicate revocation, and concurrent approvals against PostgreSQL.

![Folded access groups and denied permissions](../assets/ui-redevelopment/plugin-permission-groups-1440-light.png)

![Denied permissions on a phone](../assets/ui-redevelopment/plugin-permission-groups-390-dark.png)

Diagnostic events show the newest runtime sequence first, including a successful
native configuration load after the owned backend restart. Historical action
errors remain in the buffer. The server's Bubblewrap probe warning appears in
Plugin Manager rather than as a plugin error.

![Recent plugin diagnostics](../assets/ui-redevelopment/plugin-diagnostics-newest-1440-light.png)

![Recent diagnostics on a phone](../assets/ui-redevelopment/plugin-diagnostics-newest-390-dark.png)

The [permission UI check report](../assets/ui-redevelopment/permission-ui-conformance.json)
identifies the locally built native fixture; it does not claim these captures use
a newly downloaded distribution artifact.

These checks cover the recorded milestones. Final production and remaining
plugin integration checks are tracked separately.

## Authenticated Session Manager and native replacement

The maintained Session Manager now contributes direct **Sessions** and **Session
Manager** entries to Account and Server management. Its controls follow host
theme radii and the administrator user selector has an explicit accessible name.
Phone Settings use the space below the existing header, keep the three areas on
one row, and omit repeated area descriptions inside a selected section. A
shortcut-conflict notice stays below the phone header so navigation remains
available.

The [Session Manager report](../assets/ui-redevelopment/session-native-conformance.json)
records real authenticated owner/admin interactions at 320, 390, 1440 and 1920
pixels. Owner-only reads, clear administrator denial, foreign-session rejection,
filtering, compact tables, cancellation, targeted administrator revocation and
owner single/all revocation pass. Revoked browsers return to login without a
manual refresh; unrelated accounts remain signed in. The captures use a locally
built unsigned working-tree preview, identified by its archive SHA-256, rather
than a newly downloaded CI artifact.

![Loaded owner sessions on a phone](../assets/ui-redevelopment/session-owner-loaded-390-dark.png)

![Loaded administrator sessions on desktop](../assets/ui-redevelopment/session-admin-loaded-1440-light.png)

![Administrator sessions at 320 pixels](../assets/ui-redevelopment/session-admin-loaded-320-light.png)

Runtime gateway failures retain bounded, redacted status/detail through the host
action endpoint instead of becoming an unexplained 500. Background extension
refreshes share an in-flight load, preventing repeated polling from discarding
slow but successful contribution discovery. Account changes still invalidate
the previous account's request; explicit lifecycle mutations start a fresh load.

The [same-version native replacement report](../assets/ui-redevelopment/native-same-version-conformance.json)
starts with the downloaded Session Manager CI package, then applies the reviewed
local preview at the same version. An already-open browser reloads its native
realm automatically and requests the replacement JavaScript and CSS using the
installed payload digest. The new accessible selector and host theme radius are
active, and installation identity is retained. This checks the update behavior;
the replacement package is a local preview.

The refreshed core Settings matrix passes all 192 width/theme/role cases,
uniform titles, member administration denial, phone modal focus and overflow
checks. Frontend validation passes all 235 tests, forced type checking, lint,
formatting and the production build. The independently run backend and runtime
suites pass 1,084 tests with two existing skips, and 125 tests respectively;
configured backend Pylint remains 9.11/10.

## Production sidebar access and overflow

Committed production image `47e93aeb` passes all 24 pinned, rail and overlay
layouts in Chromium and WebKit, from 200 Ã— 280 to 1920 Ã— 1050 pixels. The resize
handle stays inside the sidebar, sticky toolbars leave the hamburger accessible,
and short menus scroll to their library, settings and account controls.

The [sidebar report](../assets/ui-redevelopment/sidebar-conformance.json) records
the exact source head and measurements. These are unmodified production checks,
not injected prototype styles. Long brand/account labels are browser-only stress
fixtures; authentication and installed navigation come from the real host.
The reproducible checker is `tools/check_sidebar_layouts.mjs`.

![Phone sidebar with long-label stress fixtures](../assets/ui-redevelopment/sidebar-overlay-320-webkit.png)

![Desktop overlay sidebar with long-label stress fixtures](../assets/ui-redevelopment/sidebar-overlay-1440-webkit.png)

## Current CI packages and gateway repair

Production host/runtime source `dd457b9d` and companion source `34852cf` pass
all 32 install/start cases from the downloaded `unsigned-dist` and
`validated-plugin-distribution` CI artifacts. The
[current package report](../assets/ui-redevelopment/current-ci-package-conformance.json)
records artifact identities, archive digests, versions and running health. These
are actual production packages, with administrator-reviewed reduced isolation,
no `NONBUBBLE_ENV`, and media-writing access withheld.

The [gateway report](../assets/ui-redevelopment/gateway-production-conformance.json)
reproduces missing callback configuration on three actual plugin actions, repairs
it using only the app's explicit callback setting, then restarts the runtime.
Jellyfin, Session Manager and Archive return HTTP 200 after both repair and
restart while the runtime callback environment variable remains omitted.
The missing case returns actionable HTTP 503 guidance; the
[missing-configuration browser report](../assets/ui-redevelopment/native-missing-gateway-conformance.json)
checks the prominent manager warning and errors inside the active native page.

![Missing callback guidance in Plugin Manager](../assets/ui-redevelopment/gateway-missing-manager-1440-dark.png)

The [native page report](../assets/ui-redevelopment/native-current-ci-conformance.json)
checks twenty loaded Jellyfin, Session Manager and Document Browser settings
pages at 320, 390, 1440 and 1920 pixels in light and dark modes. The public
`tools/check_native_plugin_ui.mjs` checker uses the real authenticated production
host and installed plugin actions.

![Current CI Jellyfin native settings](../assets/ui-redevelopment/gateway-jellyfin-settings-1440-light.png)

![Current CI Document Browser settings on a phone](../assets/ui-redevelopment/gateway-document-settings-390-dark.png)

Archive 0.0.2 contributes Cards, Sets and Bounties directly under Games, with
import directly under Account. The
[current Archive production report](../assets/ui-redevelopment/collector-current-production-conformance.json)
also checks legacy import, owned records, card/set editors, bounty objectives and
idempotent rewards, cross-user denial, global search, Home goals/reminders and
live disable/re-enable behavior. Six loaded native pages pass all four recorded
phone/desktop layouts.

![Flat Archive navigation](../assets/ui-redevelopment/archive-flat-navigation-1440-dark.png)

The appearance-selection and Session Manager content-width follow-on is
recorded below.

## Consolidated appearance and narrow native panels

Production image `a1bf2452` passes the updated installed-theme journey in
Chromium and WebKit. Appearance has one **Interface theme** selector and one
active preview. Installed styles supply the colors and shape; returning to the
native interface restores the retained preset, custom or approved plugin
palette. Browser-scoped palette styles now follow the browser choice, pause
while an installed theme is active, and return when native colors are selected.
System previews follow the current device mode.

The [Chromium report](../assets/ui-redevelopment/theme-ui-conformance.json) and
[WebKit report](../assets/ui-redevelopment/theme-ui-webkit-conformance.json)
record actual CI Forest/Purple Blocks archives, account/browser persistence,
five widths, sign-in/OIDC themes, ordinary-user administration denial and
disable/re-enable/removal. Reproduce with `tools/check_installed_theme_ui.mjs`.

![Consolidated theme selector and current preview on desktop](../assets/ui-redevelopment/theme-choice-1440-light.png)

![Consolidated theme selector and current preview on a phone](../assets/ui-redevelopment/theme-choice-390-dark.png)

Session Manager 2.3.1 is installed from actual unsigned CI artifact
`11386044038`, companion source `2236d8f`. All 32 loaded owner/administrator
layouts fit their actual host panel in Chromium/WebKit at 320, 390, 768 and
1440 pixels, in light and dark modes. Expanded GeoIP controls, long account
labels, keyboard focus and internal table scrolling pass without injected CSS.
The administrator journey uses the real Settings buttons; session data is
unchanged. The [layout report](../assets/ui-redevelopment/session-fit-conformance.json)
records package/payload provenance and each measurement. Its public checker is
`tools/check_session_layouts.mjs` in the companion repository.

![Current Session Manager on a phone](../assets/ui-redevelopment/session-fit-webkit-sessions-390-dark.png)

![Current administrator Session Manager on desktop](../assets/ui-redevelopment/session-fit-chromium-admin-sessions-1440-light.png)

The actual unsigned PWA 0.0.4 package from the same CI artifact passes the
[production PWA journey](../assets/ui-redevelopment/pwa-production-conformance.json).
Installation stays in Settings. Loaded installed-theme CSS owns offline colors
without inline palette overrides at four widths. A real stylesheet failure,
with both the HTTP and service-worker CSS caches cleared, restores the saved
native colors without changing the account's theme selection. Private APIs and
account metadata remain uncached. Disable/re-enable and explicit grant
withdrawal/restoration retire and restore the worker and its owned cache,
preserving unrelated caches. The physical OS install prompt remains manual.

![Offline native-color fallback when theme CSS is unavailable](../assets/ui-redevelopment/pwa-production-missing-theme-fallback-1440-dark.png)

All foundation CI workflows are green at `c2fd3fb`, including its production
plugin lifecycle and real session-expiry/cache acceptance. All companion checks
and host integration workflows are green at `2236d8f`; mobile PWA checks are
green at `a3e4d92`. These results close this appearance/layout milestone;
the final cross-project withdrawal, UI and merge-readiness review continues.

## Current package updates and worker recovery

Production host/runtime `688c1d66` accepts all 32 update/start cases from the
actual companion `f858db6` CI bundles: `unsigned-dist` artifact `11388472902`
and `validated-plugin-distribution` artifact `11389180378`. The
[package report](../assets/ui-redevelopment/reliability-ci-package-conformance.json)
records archive/payload digests, active versions, stable installation identities
and healthy workers. Media-writing access remains denied. A completed manual
permission review can activate an update with only the administrator's selected
new capabilities, bound to the reviewed digest; unattended updates still stage
new access for review.

The [startup report](../assets/ui-redevelopment/reliability-startup-conformance.json)
records committed image identities, sign-in, JSON errors and provider startup
before the app callback is available. Discord provider 1.2.1 retries only its
idempotent registration on temporary unavailable errors; it does not retry
permission failures or send a notification during these checks.

The [recovery report](../assets/ui-redevelopment/reliability-worker-conformance.json)
checks a runtime-only restart, restored identities/grants and all sixteen healthy
unsigned workers. Actual Jellyfin configuration, Session listing and Archive
migration-status actions return HTTP 200. A controlled worker exit exposes its
actual status in both Plugin Manager and Diagnostics; restarting clears the
failure. Bubblewrap warnings remain server-wide. The administrator's reduced
isolation acknowledgement persists without `NONBUBBLE_ENV` or a runtime callback
environment value.

The [current native report](../assets/ui-redevelopment/native-current-conformance.json)
checks twenty loaded settings pages and flat Archive placement at 320, 390,
1440 and 1920 pixels in light/dark modes, using the exact packages above.
Reproduce the browser portion with `tools/check_native_plugin_ui.mjs`.

![Current Jellyfin administration settings](../assets/ui-redevelopment/native-current-jellyfin-admin-1440-light.png)

![Current Document Browser settings on a phone](../assets/ui-redevelopment/native-current-reader-settings-390-dark.png)

![Current Session Manager at 320 pixels](../assets/ui-redevelopment/native-current-sessions-320-light.png)

All eleven UI workflow runs are green at `688c1d66`; all thirteen foundation
workflow runs are green at `19b56e7`, all four companion runs at `f858db6`, and
both template runs at `0f0afd2`. Local checks pass 1,116 backend tests (two existing
skips), 143 runtime tests, 243 frontend tests, lint/types/build, mypy on 214 files
and the 2,000-line frontend limit. Configured backend Pylint is 9.13; changed
runtime/tests score 9.27. This closes the package reliability milestone. Latest
main integration, combined contribution withdrawal and the final UI/readiness
review remain in progress.
