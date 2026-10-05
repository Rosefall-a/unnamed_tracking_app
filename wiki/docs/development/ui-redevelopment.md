# UI redevelopment: audit and design checkpoint

Status: **implemented; final CI verification in progress**. The interface uses Pocket's floating sidebar and touch-first mobile surfaces with Archive's desktop Home and overall structure. Page titles, spacing and controls use shared rules. The three original concepts remain available for future style/layout alternatives.

This page retains chronological checkpoints. Counts and work-in-progress notes in earlier sections describe those stages; use the latest integration summary below and the paired Draft PR updates for current validation.

The design concepts below are preserved interactive proposals with illustrative
data. The live application checkpoints use the Archive/Pocket design and the
explicit v1.1 contract described in the [migration guide](plugin-v1.1-migration.md).
The contract boundary, maintained plugin migration and widget/theme APIs are implemented;
final integration review is in progress. A version declaration alone does not
certify that a plugin has completed those checks.

## Selected direction and appearance foundation

The chosen hybrid is stored as `ui_style: archive-pocket`. Palette, typography, spacing, control sizes, shape, motion and elevation use semantic tokens in `src/frontend/src/styles/tokens.css`. These layers are independent so a future style can change more than colors. Only the selected hybrid is implemented today; the original Archive, Pocket and Studio proposals remain available in the gallery below and their source is preserved.

Personal Appearance settings now persist theme (`system`, `light`, `dark`), density, higher contrast and reduced motion through the existing per-user preferences API. System changes are followed only in System mode, and the device's reduced-motion preference is always respected. Compact spacing retains mobile touch targets. Queued saves and late responses are invalidated when accounts change. The navigation and page migration is in progress; appearance tokens alone do not make every existing page theme-complete.

Hosted CI on `36637321753e0ad3390b3289be215a64e303978f` passes all six workflows, including real plugin integration, strict official Jellyfin acceptance and PWA acceptance. The PWA browser check now verifies the login pathname and the preserved `return_to` query instead of incorrectly requiring a query-free login URL.

## Navigation and Settings stage

The shared shell now uses a floating desktop pane, an explicit tablet rail and phone bottom navigation with a native modal menu. Auto is the default on unconfigured devices, and existing explicit modes and stored widths are preserved. Resizing supports pointer and keyboard controls. Native modal inertness, Tab cycling, Escape and focus restoration replace the old hover/focus-blurring rail behavior. Core navigation, notification polling, upload counts and plugin capability filtering remain available.

Settings now has Preferences, Account and administrator-only Administration areas with landing groups and preserved section/tab aliases. Every area and section uses `PageHeader` and the same heading tokens. Section headings, forms, controls and surfaces use semantic theme tokens. Phones drill into a section; desktop keeps its area navigation visible. Administrator user tables become cards at narrower widths and long account values wrap. Server-wide scope is explicit. The unfinished Logs entry is removed from navigation. Completed-game badges continue to use their existing per-user storage.

The stage's browser verifier uses the compiled frontend against a real disposable backend and creates a member through the real administrator API. It checks 192 Settings screen/theme/width/role cases, matching title styles, menu focus and dismissal, no phone sidebar offset, hidden member administration UI plus a 403 from the administrator API, persisted appearance, reduced motion and page overflow. Representative actual captures and the conformance report are in the evidence directory below. No plugins are installed in the capture database, enforced by the verifier before any screenshot.

`tools/check_ui_redevelopment.mjs` requires a companion repository with Playwright installed, a disposable backend and `UI_REVIEW_USERNAME` / `UI_REVIEW_PASSWORD`. Run:

```sh
node tools/check_ui_redevelopment.mjs /path/to/plugins /path/to/evidence http://127.0.0.1:8000
```

During hosted validation, production runtime smoke exposed an asynchronous Nginx reload race: the startup document could still return HTTP 200 after status became READY. Commit `e7a028e8` waits for the compiled document before publishing readiness. The unchanged full production smoke suite passes locally and in hosted CI, including controlled configuration/database/migration/backend failures. The UI stage passes 21 frontend files / 109 tests, type check, ESLint, Prettier and production build. Remaining page/theme/plugin/widget work is still in progress.

## Baseline

`plugin-manager` was reconciled with `main` at `54056e01` on 2026-10-04. The reconciliation preserves both branches' authentication, startup, library, settings and plugin features. Host/port-scoped browser cookies now work through plugin actions, document routes, management authentication and the session gateway. Negative HTTP tests reject legacy and wrong-host cookies.

The independently published migration heads converge at `b8c7d6e5f403`. Upgrades from each previous head, fresh migration, and adoption of an existing database pass. Plugin migrations use idempotent helpers during legacy adoption; published revision identities remain intact. Future migrations start from the single current head.

Local validation:

| Check | Result |
| --- | --- |
| Backend suite, PostgreSQL 16 | 815 passed; two opt-in repository tests subsequently run separately and passed |
| Backend type check | 202 source files pass |
| Backend Pylint | 9.26/10; CI threshold 9.0 |
| Plugin runtime suite | 84 passed |
| Companion repository suite | 214 passed |
| Frontend | 19 test files / 106 tests; type check, ESLint, Prettier and production build pass |
| Wiki | Strict build passes |
| Packages | Build, distribution/source check, signature/package verification, schema validation and host contract pass across 12 maintained sources, including unreleased previews |
| Real lifecycle + browser | Discovery, consent, install, native UI, inventory during outage, sync, secrets, restart, disable/enable, retaining reinstall, update, rollback, permission staging/denial, failed-worker recovery, token confinement, purge and uninstall pass |

The real lifecycle run uses **reduced isolation**, explicitly configured by the existing acceptance harness. It does not prove strict production isolation or the eventual v1.1 per-plugin responsive matrix. Runtime isolation tests and a Linux Bubblewrap launch probe pass separately. Existing deprecation/cache warnings are recorded; Windows psycopg lacks libpq, so PostgreSQL/backend acceptance ran under WSL Ubuntu.

## Initial architecture and implications

This table records the pre-redevelopment audit. Later checkpoints below describe
the implemented replacement; it is retained to explain the original decisions.

| Area | Current implementation | Redevelopment consequence |
| --- | --- | --- |
| Frontend | Vue 3, TypeScript, Vite, lazy Vue Router views, shared reactive state modules | Extend the existing component/state architecture; do not introduce a second app or framework |
| Shell | Sidebar supports overlay/pinned/rail, remembered locally, resizable 200–440 px; default overlay | Use deliberate desktop defaults and touch navigation; preserve remembered modes without mobile content offsets |
| Product identity | Orange/graphite accents, media artwork, mixed Archive/Unnamed Tracking labels | Establish one configurable brand; keep orange identity with usable light/dark contrast |
| Styling | Dark-only global stylesheet plus partial `--ui-*` tokens and per-component hardcoded colors | Introduce semantic theme tokens for surfaces, type, spacing, density, radius, elevation and motion, then replace styles incrementally |
| Existing primitives | AppDialog, segmented tabs/controls, skeletons, tables, forms and upload views | Consolidate proven primitives rather than adding duplicate component systems |
| Preferences | Server-backed appearance/media preferences plus device-local interface preferences | Explicitly distinguish per-account settings from device-specific shell choices and server-wide branding |
| Home | Rich shelves/hero/actions with `home.replace` and `home.after-widgets` | Start minimal; add persisted user-selected widgets and a public widget lifecycle/API |
| Settings | Consolidated sections/query aliases; Account, Preferences, Library and System groups; plugin additions | Separate Preferences/Account/Administration with useful Library/Connections sections. No unfinished administrative controls. Render administration only for admins |
| Navigation | Games, collections, cards, sets, bounties; movies, TV, anime, lists; calendar, stats, notifications | Preserve the complete product inventory. Sessions/documents are plugin/context features, not invented core domains |
| Routing | Existing library/detail paths, `/plugins/:pluginId/*`, `/settings?section=…`, upload/inbox redirects | Maintain usable deep links and aliases, update internal/plugin/wiki links together |
| Shortcuts | Command palette, `?`, `/`, `n`, j/k/arrows, Enter, a–z and Escape; calendar/detail-specific handlers | Preserve editable-field guards, improve palette coverage and focus return, document conflict handling and touch equivalents |
| Plugin boundary | Capability-filtered active contributions; settings/main/admin navigation, routes, contextual actions, extension slots and replacements | Keep grants and health/compatibility checks authoritative. Disabled/uninstalled plugins must disappear immediately |
| UI hosts | Declarative UI, sandboxed iframe bridge and explicitly privileged native Vue modules | Provide documented responsive/theme APIs for each mode without widening iframe or native permissions |
| Compatibility | Manifest SDK ranges often `^1.0.0`; UI schema `v1`; plugin release version is independent | An SDK bump alone is insufficient: explicitly identify contract v1.0 vs v1.1, reject unmigrated UI against v1.1, and test newly declared support |

Existing slots include `app.global`, `home.replace`, `home.after-widgets`, `game.overview.after-header`, `game.documents.actions` and `media.detail.after-header`. Replacements must retain a working host fallback on denial, failure or deactivation. Native UI exposes Vue registration/cleanup plus host navigation/actions/settings/dialog functions; it has privileged DOM access and must retain explicit consent.

## Companion plugin inventory

Audit source: `unnamed_tracking_app_plugins` main at `9a88160b79c73ee918bc4b5bb21d4b781ae175f8`. Read manifests, entrypoints, native/sandbox assets and related tests/docs. Package release numbers such as 1.1.0 or 2.0.0 do **not** mean the new host UI contract is supported.

| Maintained source | UI/integration to migrate and verify |
| --- | --- |
| UI/API | Declarative page, action, settings, main navigation, games read |
| Playtime Report | User-scoped library report, declarative page/settings, persisted data |
| Recently Played Notifier | Games read, user notifications, settings and scheduled behavior |
| Metadata Curator | Metadata provider/search, normalized state and settings |
| Discord Delivery Provider | Delivery provider registration, notification coordination, secrets and restricted egress |
| UI Playground | Multiple sandboxed Vue pages, bridge, private storage and announcements |
| Help Button | Native routes, navigation, global overlay, dialog, Home/page replacement, contextual and settings contributions, cleanup |
| Jellyfin example | Native page/settings, identity mapping, secrets, media sync/history and event polling |
| Scoped Document Viewer | Sandboxed document reader, contextual actions, MIME/ownership confinement and mobile reader |
| Self-Service Session Manager | Native account/admin pages, scoped sessions, confirm-before-revoke and maps/privacy |
| Official Jellyfin preview | Separate identity and official signing boundary; media/plugin page integration |
| Official PWA preview | Install metadata, icons, host service worker, offline reconnect and branding propagation |

At the initial audit, the two official previews remained unreleased pending their protected signing identity and ten examples remained maintained. The completed source migration now includes twelve examples and two official previews, including `example.theme-palettes` and `example.home-widgets`. Published archives and protected official signing boundaries remain intact. Actual signed theme, widget, native settings and iframe acceptance is recorded below.

## Concepts

Use the [interactive concept gallery](../assets/ui-redevelopment/concepts.html). These share feature scope but differ in layout and interaction.

For reference before this Draft PR is merged, [download the portable gallery ZIP](https://raw.githubusercontent.com/Rosefall-a/unnamed_tracking_app/feat/ui-ux-redevelopment/wiki/docs/assets/ui-redevelopment/concept-reference.zip). Extract it and open `concepts.html`; no server or account is needed. The [local archive](../assets/ui-redevelopment/concept-reference.zip) and [instructions](../assets/ui-redevelopment/concept-reference.md) remain versioned with both original sources. The gallery can also be served by the wiki after merge.

| Direction | Desktop | Mobile | Tradeoff |
| --- | --- | --- | --- |
| Archive | Labelled persistent sidebar; balanced reading column; restrained cards; split settings | Bottom navigation plus grouped full-screen menu; stacked rows and contextual actions | Strong continuity with orange/graphite identity and clear library hierarchy |
| Pocket | Floating navigation pane; generous type; inset preference groups; editorial Home | Large touch rows; rounded cards; compact tab bar; settings as drill-down groups | Comfortable and approachable; lower information density |
| Studio | Compact sidebar plus workspace navigation; activity/list Home; table-based library | Dense but readable lists, explicit action rows and grouped menu | Efficient for larger libraries; more utilitarian than artwork-led |

Each includes desktop Home, mobile Home, desktop navigation, mobile navigation, settings landing, preferences, account, administration, a library page and a plugin page/widget. Gallery controls switch theme, viewport and user role. Widget figures and account/session data are illustrative. There is no video, thumbnail or media demo capture in this evidence.

Concept browser verification covers **480 screen/theme/width combinations**: three directions × ten screens × two themes × eight widths (320, 390, 430, 768, 1024, 1440, 1920 and 2560 px). No JavaScript errors or product-boundary overflows were found. Local interactions for theme switching, library filtering, widget selection, profile feedback and member/admin visibility pass. Captures were inspected visually. This verifies the proposals; it does not substitute for testing the eventual application.

Reproduce with Node 22+ and the companion repository's installed Playwright/Chromium:

```sh
node tools/check_ui_concepts.mjs /path/to/unnamed_tracking_app_plugins
```

The default evidence directory is `.validation/ui-concepts`. The gallery's editable fragment is `wiki/docs/assets/ui-redevelopment/concept-source.html`; `concepts.html` is its standalone preview with local carousel controls. No production route loads these files.

![Archive concept: desktop and mobile Home, settings](../assets/ui-redevelopment/archive-board.png)

![Pocket concept: desktop and mobile Home, settings](../assets/ui-redevelopment/pocket-board.png)

![Studio concept: desktop and mobile Home, settings](../assets/ui-redevelopment/studio-board.png)

## Implementation sequence after selection

1. Establish semantic tokens, layout primitives, accessible dialog/drawer/menu focus behavior and a reduced-motion policy. Keep a small component preview harness for future assembly work.
2. Add minimal storage for account appearance/Home preferences and admin branding/logo/favicon metadata, with validation and clear scope. Define theme metadata and granted theme participation; no marketplace is required.
3. Replace the shell and navigation, including persisted desktop modes, touch bottom navigation/drawer, tablet transitions and plugin-aware groups. Preserve deep links and keyboard access.
4. Rebuild Settings and Home; provide per-user widget selection/order with explicit touch alternatives to drag. Account and server settings have different explanatory copy and permissions.
5. Introduce the **v1.1.0** UI contract with explicit v1.0-only handling. Publish tokens, responsive primitives, widget registration/configuration/cleanup, capability-gated navigation/theme APIs and migration guidance.
6. Migrate maintained plugins in the companion repository, including actual mobile/native/sandbox UI work, and add a useful widget plus an **Embedded media demo widget**. Test embedded playback without recording its contents. Do not edit published packages or pretend old ranges imply migration.
7. Migrate all major content views, forms, uploads, documents, notifications and contextual actions. Replace obsolete UI only when its functionality has a proven replacement.
8. Complete the realistic plugin lifecycle matrix, ordinary/admin permission checks, routes/shortcuts/accessibility checks, and visual workflow checks at phone/tablet/laptop/desktop/ultrawide widths in light/dark/custom themes. Update implementation wiki pages only as capabilities land.

## Review checkpoint

The selected hybrid combines Pocket's floating sidebar and rounded mobile controls with Archive's desktop structure. Semantic tokens and account appearance preferences are implemented. The responsive shell and Settings now use consistent page headers, separate Account/Preferences/Administration areas, and a phone menu with focus containment and restoration. Completion badges remain personal to each account. Home now starts minimal, with the original core shelves, goals, picker and activity available as optional account-persisted widgets.

The shell checkpoint passed **192 real application combinations**: eight widths × two themes × two roles × six Settings screens. Checks include overflow, identical title typography, account preference persistence, phone menu keyboard behavior, and administrator access denial for members. The [checkpoint report](../assets/ui-redevelopment/stage-shell-conformance.json) records the results. Remaining detail/media views and the explicit v1.1 plugin boundary still require implementation and final acceptance.

![Desktop appearance preferences](../assets/ui-redevelopment/stage-shell-appearance-1440-light.png)

![Tablet appearance preferences in dark mode](../assets/ui-redevelopment/stage-shell-appearance-1024-dark.png)

![Phone appearance preferences](../assets/ui-redevelopment/stage-shell-appearance-390-light.png)

![Phone navigation in dark mode](../assets/ui-redevelopment/stage-shell-mobile-navigation-dark.png)

Reproduce against a disposable, running backend with no installed plugins:

```sh
UI_REVIEW_USERNAME=review-user UI_REVIEW_PASSWORD=review-password \
  node tools/check_ui_redevelopment.mjs /path/to/unnamed_tracking_app_plugins \
  .validation/ui-stage-shell http://127.0.0.1:55793
```

Build the frontend first. The verifier serves that compiled build, creates and removes a temporary member account, and exercises real APIs. It refuses to capture a server with installed plugins so embedded media cannot enter this evidence.

The Home checkpoint adds **48 real combinations** of minimal Home, the chooser and populated Home across the same eight widths and two themes. The [Home report](../assets/ui-redevelopment/stage-home-conformance.json) records persisted selection/order, separate account layouts, actual offline-save recovery, retained unavailable plugin selections, all nine core widgets, and real card favorite/menu behavior. Native chooser and tour dialogs contain keyboard focus and restore it on dismissal. Run the same verifier with an additional final `home` argument to reproduce; this stage creates and removes disposable game records through real APIs. Backend preference validation has 18 passing tests, and backend type checking plus all frontend checks and 109 tests passed.

![Minimal desktop Home](../assets/ui-redevelopment/stage-home-minimal-1440-light.png)

![Populated desktop Home](../assets/ui-redevelopment/stage-home-widgets-1440-light.png)

![Phone Home widgets](../assets/ui-redevelopment/stage-home-widgets-390-light.png)

![Phone Home chooser in dark mode](../assets/ui-redevelopment/stage-home-chooser-390-dark.png)

The branding checkpoint adds **48 real combinations** across the eight widths, two themes and administrator/member/public roles. The [branding report](../assets/ui-redevelopment/stage-branding-conformance.json) covers durable name/logo/favicon updates, public sign-in identity, member and anonymous write denial, malformed uploads, offline-save recovery and independent badges for two accounts. Run the same verifier with a final `branding` argument against a clean disposable server identity. The sign-in/setup styling now follows the semantic palette and phone control sizes. An account switch clears cached badges and rejects late responses from the previous account.

The real signed PWA acceptance also passes after applying custom branding: manifest names, 192/512 maskable icons and cache generations change together; revoking the PWA grant still withdraws branded assets. The original signature, consent, outage, update, rollback, disable/uninstall/reinstall and session-expiry checks remain intact. Backend regression coverage passed **847 tests** with two existing opt-in skips; mypy checks 204 files. Frontend formatting, lint, type checking, build and **112 tests** passed. The new nullable branding migration upgrades the merged published history without changing an existing revision identifier.

![Desktop app branding](../assets/ui-redevelopment/stage-branding-admin-1440-light.png)

![Phone branding controls in dark mode](../assets/ui-redevelopment/stage-branding-controls-390-dark.png)

![Public desktop sign-in with custom branding](../assets/ui-redevelopment/stage-branding-public-1440-light.png)

![Public phone sign-in](../assets/ui-redevelopment/stage-branding-public-390-light.png)

The first content checkpoint applies the shared header, palette, spacing and touch controls to Games, Collections, Cards, Sets and Bounties. Games retains Cards, List, List + preview and Shelves, together with its search, filters, presets and bulk actions. Phone List presents labelled cards with every existing field and action. Collections uses a responsive cover grid, with separate native open/delete controls. Smart collection, new card and new bounty dialogs use the shared native dialog with keyboard containment and focus restoration.

The [content report](../assets/ui-redevelopment/stage-content-conformance.json) records **160 real page/theme/width/role cases**, all four Games views at eight widths in two themes, keyboard filter selection, phone set/bounty/card creation, and actual smart collection creation, keyboard navigation and deletion. This first checkpoint precedes the detail/media review below; the complete plugin transition remains under review.

Reproduce by adding `content` as the final argument to `tools/check_ui_redevelopment.mjs` and using `.validation/ui-stage-content` as the evidence directory. The same clean-plugin-inventory guard excludes embedded-media captures.

![Desktop Games in dark mode](../assets/ui-redevelopment/stage-content-games-1440-dark.png)

![Phone Games list with the first-use bulk-edit hint](../assets/ui-redevelopment/stage-content-game-list-390-light.png)

![Desktop Bounties](../assets/ui-redevelopment/stage-content-bounties-1440-light.png)

![Phone smart collections](../assets/ui-redevelopment/stage-content-smart-collections-390-dark.png)

The detail/media checkpoint applies semantic surfaces, text, status colors and control sizes to game details, populated collections and sets, the card designer, all three media libraries and details, media lists and statistics. The shared phone media bar keeps its account controls beside the library selector and groups layout/list controls below it. Artwork, card metals and trophy colors retain their meaning; the surrounding menus and editors follow the selected appearance. Shared editors, calendar, notifications and achievement details also use the same palette.

The real review covers **416 populated page/theme/width/role cases**, including a card assigned to its set, all five statistics tabs and visible empty heatmap days. The installer, upload-limit enforcement and navigation checks are part of the ongoing combined review. Source-compatible plugin UI migration and custom palette acceptance continue independently before this draft is completed.

![Phone Movies in light mode](../assets/ui-redevelopment/stage-detail-movies-390-light.png)

![Desktop Movies in dark mode](../assets/ui-redevelopment/stage-detail-movies-1440-dark.png)

![Desktop Statistics in dark mode](../assets/ui-redevelopment/stage-detail-statistics-1440-dark.png)

![Phone populated set in light mode](../assets/ui-redevelopment/stage-detail-sets-390-light.png)

The dialog checkpoint uses wider desktop space for Home customization, installation permission review and plugin settings. Home selection/order and installer methods/catalogue sit side by side at wider sizes, while phones retain a single column. The [dialog report](../assets/ui-redevelopment/stage-dialogs-conformance.json) records **64 real Home and plugin-management cases** across eight widths in light/dark mode, persisted settings and account isolation, keyboard containment, focus restoration and offline-save recovery. Manager settings save even when the runtime is disconnected; existing package history remains intact and the UI explains that later package operations apply the saved retention limit. Reproduce with the `home` review stage above.

![Desktop Home selection and ordering](../assets/ui-redevelopment/stage-home-chooser-1440-light.png)

![Desktop Home chooser in dark mode](../assets/ui-redevelopment/stage-home-chooser-1440-dark.png)

![Wide plugin installer in dark mode](../assets/ui-redevelopment/stage-plugin-installer-1440-dark.png)

![Phone plugin installer](../assets/ui-redevelopment/stage-plugin-installer-390-light.png)

The palette and sign-in checkpoint adds Orange, Green and a custom editor with separate light/dark colors, semantic menu/control previews and contrast validation. The [palette report](../assets/ui-redevelopment/stage-palette-conformance.json) records **832 populated cases** using Green and Custom across eight widths, both themes and two roles, in addition to the earlier Orange review. The browser bars and public sign-in use a bounded cosmetic device cache; authenticated account preferences replace it after login. The [OIDC report](../assets/ui-redevelopment/oidc-theme-conformance.json) records **12 real RS256 authorization-code flows** across phone/desktop, three palettes and both modes, including hidden entrypoints, manual provider buttons, invalid-state errors, local fallback, return paths and member authorization. Changed provider configuration replaces Authlib's cached client without requiring a restart. Frontend regression coverage passed 133 tests; mypy passed all 204 backend files, and the backend retains a 9.27/10 Pylint score against the existing 9.0 CI requirement.

![Custom desktop palette preview](../assets/ui-redevelopment/stage-palette-preview-1440-dark.png)

![Phone SSO buttons in a custom light palette](../assets/ui-redevelopment/oidc-login-390-light.png)

![Desktop SSO buttons in a custom dark palette](../assets/ui-redevelopment/oidc-login-1440-dark.png)

The original gallery and captures remain available in this wiki and Git history as a shared reference, separate from production screenshots. The Draft PR remains a living record and targets `plugin-manager`. The production readiness race discovered in CI is fixed. At `97e8405a`, companion integration found an obsolete official Jellyfin capture selector on the old Settings landing page. Companion commit `fef5b7b` uses the preserved Settings deep link and retains the existing interaction assertions. The unchanged strict container acceptance then passed locally with the committed host checkpoint and paired companion fix: actual package installation, consent, privileged reauthentication, account/server configuration, sync, update/state retention, admin/user separation, viewing history, Watch Now and phone layout. All seven workflows passed at the pushed Home checkpoint `5896d8c9`. Each new stage must pass CI independently.


The appearance refinement checkpoint replaces floating-star ribbons with a shared folded, notched ribbon in saved game cards and the personal settings preview. The preview reuses the host's default game-cover generator and selects one of eight playful titles on refresh; it never creates a library entry. The [ribbon report](../assets/ui-redevelopment/stage-ribbon-conformance.json) records 24 preview/saved-card checks covering all four corners, both themes and 320/390/1440-pixel widths, with unchanged settings for another account.

Custom contrast guidance is now advisory and expandable: every valid color can be saved. The preview starts with the displayed theme and follows app/System changes, while retaining manual light/dark inspection. Portable palette JSON includes both color sets and no account data. Imports populate the unsaved preview; malformed, unsupported, oversized or non-color values are rejected without replacing saved preferences. The [sharing report](../assets/ui-redevelopment/stage-palette-sharing-conformance.json) verifies actual download/import round trips, low-contrast save/reload, theme following and account isolation. This supersedes the editor-blocking behavior in the historical 832-case palette checkpoint; its populated-page coverage remains applicable.

![Phone ribbon preview](../assets/ui-redevelopment/stage-ribbon-preview-390-dark.png)

![Saved completed game ribbon](../assets/ui-redevelopment/stage-ribbon-card-dark.png)


The notification/navigation checkpoint replaces the notification popup's fixed dark colors with semantic palette roles and gives the selected bell a solid accent with contrasting icon. Scroll rows retain their height so long messages do not overlap; opening focuses a control and Escape restores the bell. Navigation selection collapses an expanded icon rail, including selecting the current page. The [topbar report](../assets/ui-redevelopment/stage-topbar-conformance.json) records 48 populated popup cases across eight widths, three palettes and light/dark modes, plus real icon-rail navigation checks.

![Phone notification popup in light mode](../assets/ui-redevelopment/stage-notifications-390-light.png)

![Desktop notification popup in dark mode](../assets/ui-redevelopment/stage-notifications-1440-dark.png)


## Shared game and media editors

Game create/edit, list create/edit, media quick add/edit, notes and completion rating now use the shared native dialog, theme surfaces, focus containment and Escape dismissal. Content-heavy search/edit dialogs use up to 1120 pixels on desktop. Media list action columns reserve space for all three touch targets, preventing progress cells from covering Edit.

The [editor report](../assets/ui-redevelopment/stage-editors-conformance.json) records 160 real browser checks across eight widths and both themes, including note saves through the real API. The capture database has no installed plugins.

![Wide desktop movie editor](../assets/ui-redevelopment/stage-media-add-1440-light.png)

![Phone movie editor in dark mode](../assets/ui-redevelopment/stage-media-add-390-dark.png)


## Search, shortcuts and combined personal settings

Search library now loads on the sidebar's first open, survives a failed source with cached results and Retry, and searches real movie/TV/anime endpoints. Account changes invalidate pending queries and private results. Administrator and plugin links retain their visibility checks. Keyboard help prioritizes the current route and uses expandable sections shared with Settings. Navigation and search keys work across core pages, while cached inactive libraries, typing and open dialogs do not receive page shortcuts.

Appearance and Interface now share one page with theme/layout, navigation/library defaults and completed-game badges. Both previous deep links remain supported; device-specific defaults retain their original storage and account appearance retains its existing per-user API.

The [search report](../assets/ui-redevelopment/stage-search-conformance.json) records 52 browser cases plus real matching, navigation, delayed loading, retry and role checks. The [combined-settings report](../assets/ui-redevelopment/stage-settings-combined-conformance.json) records 32 cases across eight widths and both themes, including persisted device defaults. Frontend formatting, lint and type checks passed; all 152 current unit tests passed.

![Search across games and media](../assets/ui-redevelopment/stage-search-library-desktop.png)

![Expandable help with the current page first](../assets/ui-redevelopment/stage-shortcuts-current-page.png)

![Combined appearance and interface controls](../assets/ui-redevelopment/stage-settings-combined-1440-light.png)


## Alt navigation and hover hints

Page navigation now uses Alt plus the displayed letter instead of a two-key sequence. Sidebar links expose matching hover titles and `aria-keyshortcuts`, including the collapsed rail; expandable groups explain which page their key opens. Search retains Ctrl/Cmd + K. Help and Settings share the new mappings. Option-produced symbols on macOS are resolved from the underlying key, while AltGr, other modifier chords, typing, IME, repeated keys and open dialogs retain their existing behavior.

The [updated navigation report](../assets/ui-redevelopment/stage-alt-navigation-conformance.json) repeats 52 route/theme/width checks using actual Alt navigation and verifies title hints, typing and editor guards. It supersedes the earlier sequence mappings without changing the earlier evidence.

![Help with Alt page navigation](../assets/ui-redevelopment/stage-shortcuts-alt-navigation.png)

### Settings installation and offline appearance

App installation now lives in **Settings → App installation**, with browser
prompt, installed status, recovery, and iOS guidance. Persistent installation
controls no longer cover the top bar. The neutral offline page follows the
current Light, Dark or System mode and personal palette without caching account
data. See [PWA integration](https://github.com/Rosefall-a/unnamed_tracking_app/blob/feat/ui-ux-redevelopment/docs/official-pwa.md).

The [signed PWA report](../assets/ui-redevelopment/pwa-conformance.json) covers
installation, consent, invalid signatures, branding changes, permission
withdrawal, worker/cache migration, rollback, expiry and offline recovery,
including 18 width/palette/mode cases. OS installation remains a physical-browser
check; automation exercises the browser prompt event boundary in Settings.
Responsive captures wait for the navigation transition and assert no overflow.

![Phone installation settings](../assets/ui-redevelopment/pwa-settings-install-390.png)
![Desktop installation settings](../assets/ui-redevelopment/pwa-settings-install-1440.png)
![Custom light offline palette](../assets/ui-redevelopment/pwa-custom-offline-light.png)
![Custom dark offline palette](../assets/ui-redevelopment/pwa-custom-offline-dark.png)

## First-login appearance and cosmetic cookies

Each account receives a welcome dialog once, with Light/Dark/System, Orange/Green, spacing and accessibility choices. Menu/card previews follow the chosen mode without changing the account until Save & continue succeeds. Completion uses the existing per-user JSON preference store and requires no schema migration. Failed saves retain the choices and leave completion false.

The allowlisted, versioned `uta-ui-preferences` cookie stores cosmetic values only, with Path=/, SameSite=Lax, a one-year lifetime and Secure on HTTPS. Account preferences remain authoritative after sign-in. The existing cosmetic local-storage cache remains available for the PWA offline shell. Neither cache stores identity, credentials or onboarding state.

The [welcome report](../assets/ui-redevelopment/stage-welcome-conformance.json) covers eight real new-account phone/desktop Light/Dark flows, account persistence, one-time completion, a failed save followed by retry, and cookie-only sign-in restoration after clearing local storage. Three cookie regression tests cover flags, malformed/oversized input, discarded extra fields and blocked storage; backend tests check strict boolean validation and account isolation.

![Phone first-login appearance choices](../assets/ui-redevelopment/appearance-welcome-390-dark.png)
![Desktop first-login appearance choices](../assets/ui-redevelopment/appearance-welcome-1440-light.png)

## Settings placement and a separate Upload destination

Plugins can place settings pages in Account, Preferences or Administration and choose a plain-text group label through the public contribution contract. Administration requires administrator-only visibility; capability grants and action authorization remain independent. Jellyfin personal sync and personal sessions use Account, server controls and document limits use Administration, and Help uses Preferences. The primary sidebar highlights the resolved area instead of guessing from section IDs.

Upload now opens its own sidebar page. The same upload/assignment/trash services are retained, with keyboard-accessible thumbnail selection and the shared deletion dialog. Legacy inbox/settings links redirect to the new destination. Visual review also corrected the shared dropzone's light-mode text and semantic palette colors, and moved task progress above phone navigation with accessible dismissal.

The [Upload report](../assets/ui-redevelopment/stage-upload-conformance.json) records twelve real Light/Dark cases from 320 to 1920 px, actual PNG uploads, keyboard selection, dialog cancellation, deletion/restoration, phone toast placement, legacy redirects and Administration highlighting for five sections. Placement validation and administrator-boundary tests passed; all 169 frontend tests and 220 companion source/package tests passed.

![Standalone phone Upload page](../assets/ui-redevelopment/upload-page-390-dark.png)
![Standalone desktop Upload page](../assets/ui-redevelopment/upload-page-1440-light.png)

## Direct plugin discovery and retained releases

Plugin installation now has one Discover view with separate Official, Example and Community/unverified groups, tag/source filters and a release selector. Package/URL acquisition uses a spacious separate dialog with side-by-side methods on desktop. Installed plugins expose manager controls, native settings access and diagnostics. Incompatible releases explain the failing contract before the long metadata, including on phones.

Older catalogue installs and rollback persist a version pin and disable automatic updates. Reinstall retains the pin; failed commit/activation restores the prior policy. A manual latest update preserves an explicit disabled-update preference, while explicit Enabled/Follow selection releases a pin. Historical archive signatures and hashes remain unchanged.

The [responsive discovery report](../assets/ui-redevelopment/plugin-discovery-conformance.json) covers twelve real Light/Dark cases from 320 to 1920 px, actual catalogue history/review, grouped examples, dialogs and overflow checks. Backend catalogue/lifecycle coverage passed 312 tests before two added transaction-policy regressions, which also passed. All 172 frontend and 220 companion source/package tests passed. The prior paired commits passed all seven host and both companion CI workflows; fresh installer CI and final complete acceptance are recorded in subsequent PR updates.

![Phone grouped plugin discovery](../assets/ui-redevelopment/plugin-discovery-390-dark.png)
![Desktop grouped plugin discovery](../assets/ui-redevelopment/plugin-discovery-1440-light.png)
![Phone package or URL installer](../assets/ui-redevelopment/plugin-package-chooser-390-dark.png)
![Desktop package or URL installer](../assets/ui-redevelopment/plugin-package-chooser-1440-light.png)


## Native library and calendar workflow review

Calendar event, manual history and subscription dialogs now use the shared native modal with focus containment, Escape and focus restoration. Event and history editors use available desktop space and retain phone touch controls. The random game picker uses the same spacious modal. The media rating arrow and destructive hover state follow semantic palette colors.

The [workflow report](../assets/ui-redevelopment/library-workflow-conformance.json) covers four real phone/desktop light/dark cases: game creation, saved ratings and completion dates, random selection, movie rating bounds/save/clear, saved calendar events and manual history, and calendar subscription focus/dismissal. Subscription credentials are excluded from screenshots. All 175 frontend tests, formatting, lint, type checking and production build pass at this checkpoint.

![Saved game ratings on a phone](../assets/ui-redevelopment/game-workflow-390-dark.png)

![Spacious desktop random picker](../assets/ui-redevelopment/random-picker-1440-light.png)

![Phone history editor](../assets/ui-redevelopment/calendar-history-390-dark.png)

![Desktop history editor](../assets/ui-redevelopment/calendar-history-1440-light.png)


## Keyboard navigation inside maintained plugins

Global Alt navigation includes Upload (Alt+U) and Notifications (Alt+O), with hints derived from the same binding table as keyboard help. Installed opaque plugin frontends receive advertised navigation keys through the public SDK and forward only supported keys. The SDK also forwards advertised host help (`?`) and search (Ctrl/Cmd+K) without leaving the plugin page. Host dialog and command-palette guards remain authoritative. Arbitrary paths are rejected.

The [updated search/navigation report](../assets/ui-redevelopment/stage-search-conformance.json) passes 60 real core route/theme/width cases plus search, offline retry, editable-field guards, create dialogs and account separation. The [signed plugin report](../assets/ui-redevelopment/plugin-appearance-final.json) also passes six actual navigation cases and four native search/help dialog cases from inside the Document reader frame, a rejected arbitrary path and an open host-dialog guard. All 41 public SDK/document-browser tests and 220 companion tests pass.

This sweep exposed plugin notifications crashing the old media-only list. The list now displays plugin and unfamiliar kinds safely, includes a Plugins filter, and retains read/unread/remove actions. Notifications without a media target do not fabricate an Anime link; the bell opens the notification list. All 180 frontend tests and quality checks pass after the fix.

## Current integration summary

The final native review passes 160 real content/theme/width/role cases, 416 populated detail/media/settings cases, and another 832 cases using Green and a custom palette. The [palette report](../assets/ui-redevelopment/stage-palette-conformance.json) includes arbitrary valid colors with advisory contrast guidance, current-mode preview, portable download/import, account separation and System switching. The installer and calendar dialogs use the corrected shared focus handler, including collapsed sections.

The complete local backend suite passes 955 tests with two existing opt-in skips; signed repository acceptance exercises the cross-repository paths separately. Mypy passes 204 files and Pylint scores 9.27/10 against the current 9.0 threshold. All 180 frontend tests and frontend quality/build checks pass. Maintained companion validation passes 220 tests, fourteen source contracts and 41 public SDK/document-browser checks. The PWA assets pass twelve Node tests.

Actual signed package acceptance passes native Jellyfin/Document Browser settings, iframe reader, themes/widgets, account separation, permissions, acquisition, historical version pins, updates, rollback, runtime outages and failure recovery. Strict production Docker/Bubblewrap acceptance passes the official Jellyfin preview using an isolated Jellyfin protocol fixture; it is not a claim of testing a deployed Jellyfin server. PWA browser acceptance passes Settings-based installation, early prompt timing, branding, online/offline custom palettes, updates, rollback, permission withdrawal, uninstall/reinstall and session expiry. Headless install coverage verifies the prompt event boundary rather than a physical operating-system prompt.

The [open-PR integration review](ui-pr-integration-review.md) records exact overlapping heads and preservation plans. The `plugin-manager` target is an ancestor and has a clean merge tree; its full suites were checked independently. Cards, Sets and Bounties remain in this redesign. Final CI results and exact matching host/companion heads are recorded on the Draft PRs before completion.

## Phone Library and Media navigation follow-up

The bottom tabs now remain in the native navigation dialog's top layer while it is open, so Library and Media can switch without blocked touches. Switching a category reveals its links at the top of the menu. Queued close events cannot dismiss a reopened pane, and Home also dismisses the menu when already on Home. Closed phone dialogs retain their target for reliable tab relocation; tablet and desktop behavior is preserved.

The [touch navigation report](../assets/ui-redevelopment/mobile-navigation-conformance.json) passes eight real Light/Dark cases at 320, 390, 430 and 760 pixels, repeated section and route changes, focus containment, Escape, Home dismissal and phone/tablet resizing. All 180 frontend tests, formatting, lint, type checking and production build pass. Cards, Sets and Bounties remain available; main's removal changes were not synchronized.

![Phone navigation in light mode](../assets/ui-redevelopment/mobile-navigation-light.png)

![Phone navigation in dark mode](../assets/ui-redevelopment/mobile-navigation-dark.png)

## Personal and plugin keyboard shortcuts

Preferences now offers a master switch and individual enabled states, editable
combinations, key recording and restored defaults. Personal changes use the
existing per-account preference store. A conflicting binding is disabled while
the oldest enabled binding keeps its keys. Activation order survives reloads;
re-enabling or remapping a binding gives it a new claim on those keys.
Hover tooltips, current-page-first expandable help, plugin frames and the guided
tour all use the same active bindings. Disabled shortcuts leave clickable tour
controls available. Cards, Sets and Bounties are now supplied by the official
Collector's Archive plugin rather than the core shortcut list.

The [shortcut settings report](../assets/ui-redevelopment/shortcut-settings-conformance.json)
covers recording, persistence after reload, conflict priority, master disable
and a clickable tour in four Light/Dark cases from 320 to 1920 px. Search and
navigation checks pass another 48 core route/theme/width combinations, local
search/create controls, typing guards, dialog containment and account separation.
All ten guided tour steps also pass on Light/Dark desktop and phone layouts.
Frontend type, lint, format, build and 203 unit tests pass; backend validation
passes 1,020 tests with two existing opt-in skips, mypy and Pylint at 9.08/10.

![Desktop shortcut conflict guidance](../assets/ui-redevelopment/shortcut-conflict-1440-light.png)

![Phone shortcut conflict guidance](../assets/ui-redevelopment/shortcut-conflict-390-dark.png)

### Conflict ownership and linked notices

The updated host disables conflicting newcomers by default and shows a themed
notice linking directly to the affected key editor. If Search is disabled and
the example claims Ctrl/Cmd+K, re-enabling Search cannot take those keys back.
Remapping to unused keys can enable the repaired binding. Disabled bindings
stay off even when their previous owner disappears. Discovery waits for account
preferences; a failed save keeps the local disabling and offers Retry, and logout
clears private notices and queued changes.

The [installed-plugin report](../assets/ui-redevelopment/shortcut-priority-conformance.json)
verifies this sequence, real dispatch, linked remapping, reload persistence,
random shortcut execution/removal and plugin disable/re-enable at 320, 390,
1440 and 1920 pixels in Light/Dark modes. These checks used disposable installed
packages, including a locally built example; they are not an assertion about
downloaded final CI artifacts. The public harness's `shortcut-priority` stage
requires only the Shortcut Playground example to be installed.

The latest milestone passes 228 frontend tests, 1,071 backend tests with two
existing skips, forced typing/build/lint/format/source-size checks and strict
documentation. Backend Pylint remains 9.11/10; the changed shortcut validator is
10/10. The example's wording documents the same ownership rules.

![New conflict notice](../assets/ui-redevelopment/shortcut-new-conflict-1440-light.png)

![Default Search disabled while the older plugin owns the keys](../assets/ui-redevelopment/shortcut-oldest-owner-390-dark.png)

## Background task controls and save feedback

The Tasks page now uses theme surfaces and stronger field borders, shows interval
validation beside the edited field and preserves unsaved drafts when another task
is saved. The "All changes saved" confirmation lasts twelve seconds, followed by
a quiet "Saved" state. Scrollbars follow the active theme in native pages and
plugin frames.

Plugins can declare bounded v1.1 schedules using the existing scheduler, with
interval, on/off and Run now controls. They start off and run under the approved
background administrator identity. Live grants, lifecycle, no-overlap and action
limits apply; only a bounded public result summary is retained. The UI/API
companion example demonstrates this public contract.

The [task controls report](../assets/ui-redevelopment/tasks-ui-conformance.json)
passes four real light/dark layouts from 320 to 1920 pixels, field errors, draft
preservation and timed save feedback. Backend checks pass 1,037 tests with two
existing opt-in skips, mypy over 212 files and Pylint at least 9.09/10; all 101
runtime tests and 207 frontend tests pass. Companion validation passes 241 tests
and all sixteen generated packages pass actual host verification, installation
and disabled lifecycle checks. Enabled plugin schedule checks remain part of the final
cross-repository acceptance.

![Light-mode task controls and inline validation](../assets/ui-redevelopment/tasks-validation-1440-light.png)

![Phone task controls in dark mode](../assets/ui-redevelopment/tasks-validation-390-dark.png)

## Responsive library layouts and phone interaction

Games, Movies, TV and Anime now use distinct phone densities: Small fits three
columns, Medium two and Large one. Virtual rows use the same available width as
the CSS grid. Resize observers coalesce updates into animation frames; the
virtualizer also delivers resize measurements on animation frames, eliminating
WebKit's resize-observer loop errors during navigation and layout changes.

On phones, search and density stay visible while Controls reveals sorting,
filters and bulk actions. The account chip appears once in the global header.
Cards expose a 44-pixel More button with native themed action dialogs. Game
Preview fits the available viewport above the bottom navigation, shows its title
immediately and scrolls its picker and details independently. All existing
favorite, collection, edit, note and media episode actions remain available.

The [Chromium report](../assets/ui-redevelopment/library-chromium-conformance.json)
and [WebKit report](../assets/ui-redevelopment/library-webkit-conformance.json)
each pass 198 checks across 320, 390, 430, 760, 768, 1024, 1440 and 1920-pixel
viewports in light/dark mode, with owned sample records in all four libraries.
Checks cover all views, density, card actions, local search/create shortcuts,
phone navigation and viewport bounds. These are browser-engine tests against a
local isolated backend, rather than a physical iPhone or network benchmark.

Frontend formatting, lint, types, production build and all 207 unit tests pass.
The frontend workflow now enforces the requested 2,000-line source-file limit;
all 302 files pass, with the largest at 1,973 lines.

![Phone game shelf in WebKit](../assets/ui-redevelopment/webkit-library-game-shelves-390-dark.png)

![Phone game preview in WebKit](../assets/ui-redevelopment/webkit-library-game-preview-390-dark.png)

![Phone movie shelf in WebKit](../assets/ui-redevelopment/webkit-library-movie-shelf-390-dark.png)

![Desktop movie board in light mode](../assets/ui-redevelopment/webkit-library-movie-board-1440-light.png)

## Package drops and server isolation approval

Drop one `.utp`, `.upt` or `.zip` package onto the install controls to open its
verified upload review directly. Invalid archives, multiple files and oversized
packages are rejected. The file picker and existing publisher, compatibility,
permission and administrator-password reviews remain available.

When Bubblewrap is unavailable, an administrator can acknowledge reduced
isolation for the whole server in Plugin Manager. No environment override is
required. Approval survives restarts, retains a persistent warning and can be
withdrawn in manager settings. Withdrawal stops affected workers while retaining
their packages and data. An optional `NONBUBBLE_ENV=true` deployment override
suppresses the prominent warning; diagnostics still report the actual mode.

The real CI archives from companion run `37295244287` supplied sixteen packages
each. All thirty-two verified installs started healthy without the environment
override. Withdrawal, actionable startup rejection, approval and runtime restart
also passed. Browser acceptance exercised both file extensions, invalid uploads,
the required acknowledgement, resumed installation and withdrawal in settings.
See the [CI-package report](../assets/ui-redevelopment/ci-isolation-conformance.json)
and [browser report](../assets/ui-redevelopment/isolation-and-drop-conformance.json).

![Dropped package review on desktop](../assets/ui-redevelopment/package-drop-review-1440-light.png)

![Phone isolation acknowledgement](../assets/ui-redevelopment/isolation-acknowledgement-390-dark.png)

![Persistent phone isolation warning](../assets/ui-redevelopment/isolation-approved-390-dark.png)

## Updating dropped packages and confirming release changes

Installed plugin cards, their **Upload update** controls and the persistent
action row above the plugin tabs accept package drops. The general install
controls also recognize an installed plugin and open its update review directly.
Dropping a different plugin onto an installed plugin reports the mismatch in
the active dialog. Invalid-file warnings receive focus and use the native
light/dark error colors.

Applying the installed version again requires a separate confirmation. An older
release has a prominent yellow downgrade confirmation, is pinned and disables
automatic updates. Reapplying that pinned version retains the pin and update
policy. The backend verifies the reviewed digest and installed-version snapshot;
confirmation cannot bypass publisher identity, compatibility or permission
review. Upload, URL and catalogue transports share these checks.

The [update workflow report](../assets/ui-redevelopment/plugin-update-conformance.json)
records actual runtime/browser checks at 320, 390, 1440 and 1920 pixels. These
checks use locally built maintained example code and a private lower-version
variant; they do not claim to validate downloaded CI archives. Same-version
cancellation/application, downgrade pinning, all four drop targets, installation
identity and visible failure focus pass. Backend validation passes 1,080 tests
with two existing skips, mypy over 212 files and the configured Pylint gate at
9.11/10. Frontend validation passes 231 tests, lint, formatting, forced types,
production build and the 2,000-line source guard.

![Desktop downgrade confirmation](../assets/ui-redevelopment/plugin-downgrade-confirmation-1440-light.png)

![Phone same-version confirmation](../assets/ui-redevelopment/plugin-same-version-confirmation-390-dark.png)

![Update error in the active phone dialog](../assets/ui-redevelopment/plugin-update-active-error-390-dark.png)

## Coupled production and Collector's Archive checkpoint

The current Nginx production image starts with encoded database credentials,
preserves data across restart, signs in without a refresh and returns JSON for
unknown API routes. Both downloaded CI bundles from companion commit `b58359b`
pass 32 actual consent/install/start checks; all sixteen final unsigned workers
are healthy. Whole-server reduced-isolation approval survives restart with
`NONBUBBLE_ENV` absent. The [package report](../assets/ui-redevelopment/production-ci-package-conformance.json)
records the exact archive IDs and package hashes.

Collector's Archive passes [the production browser workflow](../assets/ui-redevelopment/collector-ui-conformance.json)
with actual new-account imports, owned Cards/Sets/Bounties, objectives, evidence,
journal entries, idempotent points, card/set creation and edits, cross-user denial,
global search, Home goals, deadline reminders and disable/re-enable recovery.
Six loaded pages at 320/light, 390/dark, 1440/light and 1920/dark have no viewport
or sidebar overflow and no browser exceptions. Mobile pages reclaim the spare
top padding. These are downloaded CI packages, not a local preview build.

![Actual CI Bounties on a phone](../assets/ui-redevelopment/collector-loaded-bounties-dark-390.png)

![Actual CI Cards on desktop](../assets/ui-redevelopment/collector-loaded-cards-light-1440.png)

### Remaining integration queue

This is a progress checkpoint. The coordinated PRs remain in progress until the
following work is verified and their current heads pass CI:

- Recheck all maintained plugins using the latest downloaded CI packages.
  Authenticated Session Manager owner/admin revocation and native replacement
  now pass; see the [native review](native-plugin-review.md). Preserve limited
  legacy compatibility and the v1.1 boundary.
- Preserve the completed Collector's Archive checks in the final combined
  production and theme review.
- Check contribution cleanup after permission withdrawal, plugin disable and
  master disable, including Tasks, shortcuts, native styles, settings placement
  and reviewed page overrides.
- Validate the new basic themes repository and administrator installation page
  in production, including server defaults and account/device choices. Its
  builder and branch CI pass; host regression tests and frontend checks pass.
- Recheck the paired host heads against main and current open PRs. Main is
  integrated, intentional Games/Media changes are preserved and inherited
  Plugin Manager source-size checks pass; verify these remain true at completion.
- Run the latest coupled production container with its database and runtime,
  including JSON startup/error responses, OIDC, cookies, onboarding, PWA
  settings installation, offline themes and restart recovery.
- Complete the final light/dark/custom-theme and phone/desktop review, current
  open-PR overlap audit and template/API documentation check. Keep screenshots
  and full-scope PR updates current; mark PRs ready only after their checks pass.
- Assess the low-priority Playnite extension download integration and document
  feasibility, adding it only if the existing interfaces make it straightforward.

## Installed themes and current production packages

The basic themes repository now builds inert `.utt` CSS packages for Forest and
Purple Blocks. Administrators install them through a separate, simpler Themes
page, review publisher/version details, choose a server default, disable or
remove packages. Users select their own theme and choose account or browser
storage. There are no theme workers or automatic updates.

The [production theme report](../assets/ui-redevelopment/theme-ui-conformance.json)
uses downloaded artifact `11379738621` from themes commit `cf22e35`, with exact
package hashes. Metadata review, square sidebar controls, independent account
and cosmetic-cookie choices, reloads, administrator denial, server defaults,
sign-in/OIDC, disable/re-enable and removal pass. Fifteen captures cover 320,
390, 768, 1440 and 1920 pixels. Recorded measurements verify the actual sidebar
and resolved scrollbar colors. An older hard-coded dark rule on `html` was
removed so the shared theme rules can apply.

The [current CI-package report](../assets/ui-redevelopment/production-ci-package-conformance.json)
records 32 actual install/start checks from companion commit `ec372bf`, including
PWA `0.0.3`. All sixteen final unsigned workers remain healthy after restarting
the committed production container. Reduced-isolation acknowledgement persists
without an environment override. The current host, companion, PWA and theme
heads pass their CI workflows; remaining combined browser checks are still in
progress.

![Server theme management](../assets/ui-redevelopment/themes-manager-1440-light.png)

![Square Purple Blocks interface](../assets/ui-redevelopment/theme-purple-appearance-1440-light.png)

![Purple Blocks on a small phone](../assets/ui-redevelopment/theme-appearance-320-light.png)

![Themed sign-in](../assets/ui-redevelopment/theme-sign-in-390-dark.png)
