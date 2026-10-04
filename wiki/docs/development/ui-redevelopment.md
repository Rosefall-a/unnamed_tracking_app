# UI redevelopment: audit and design checkpoint

Status: **direction selected; implementation in progress**. Use Pocket's floating sidebar and touch-first mobile surfaces with Archive's desktop Home and overall structure. Keep shared title, spacing and control rules consistent across pages. Preserve the three original concepts for future style/layout alternatives.

The design concepts below are preserved interactive proposals with illustrative
data. The live application checkpoints use the Archive/Pocket design and the
explicit v1.1 contract described in the [migration guide](plugin-v1.1-migration.md).
The contract boundary is implemented; full plugin UI migration, widget/theme APIs
and final acceptance are still in progress. A version declaration alone does not
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

## Current architecture and implications

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

The two official previews remain unreleased pending their protected signing identity. Ten example sources remain maintained; stale host documentation incorrectly describing six as retired was corrected during reconciliation. No maintained standalone theme plugin currently exists, and the new Home widget demonstration does not exist yet. Both are explicit future coverage rather than fabricated compatibility evidence.

## Concepts

Use the [interactive concept gallery](../assets/ui-redevelopment/concepts.html). These share feature scope but differ in layout and interaction.

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
