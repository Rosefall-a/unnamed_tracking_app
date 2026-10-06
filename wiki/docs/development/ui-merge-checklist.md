# UI merge: remaining acceptance checks

Updated 2026-10-06 after integrating main `6244677` through Plugin Manager.
This exports outstanding verification under the user's final merge-preparation
scope. It is not a claim that every scenario passes.

## Completed integration gates

- [x] Resolve main → Plugin Manager and Plugin Manager → UI conflicts; preserve functional main changes and the redesigned interface.
- [x] Run complete local backend/frontend checks, configured Ruff/Pylint and the unwaived 2,000-line UI source guard.
- [x] Build the actual committed production image, sign in directly and retain runtime/data/plugin identity/grants.
- [x] Check the revoked-key boundary against a valid browser cookie; verify production API JSON and private-log denial.
- [x] Recheck WebKit phone navigation, 198 loaded library layouts, the real guided tour and native settings.
- [x] Export confirmed existing-session Archive restoration behavior as [#430](https://github.com/Rosefall-a/unnamed_tracking_app/issues/430).
- [x] Refresh coordinated PR scope/screenshots/dependencies and verify companion/template/PWA/theme CI before marking drafts ready.

## Browser and production checks still to perform

- [ ] **Editor matrix:** adapt `tools/check_library_editors.mjs` to expand the collapsed phone Library controls before using Create. Respect the new final Page step in Add Game. Re-run its game/media editors, notes, file/archive controls and native focus/validation checks across light/dark and phone/desktop. Its last timeout targeted a hidden control; that is not established as a product bug.
- [ ] **Obsolete content stage:** update `tools/check_content_ui.mjs` for current core routes. Its old core Cards/Sets/Bounties APIs are intentionally gone. Keep the real official Archive CRUD/ownership/import suite instead of restoring removed core features to satisfy that checker.
- [ ] **Native restore/withdrawal:** resolve or reproduce #430 on the final product head; distinguish readiness propagation from cached import failure. Then complete loaded settings/routes/shortcuts/Home widgets, theme CSS, reviewed overrides and host-managed Tasks disable/re-enable/revoke/regrant. The combined run stopped at Archive restore; later cases were not reached. Always restore original grants/preferences and confirm installation identity/digest.
- [ ] **Collector's Archive:** run final-head create/edit/delete, ownership and legacy import with fresh owned accounts. The retained administrator fixture has `imported:false`; its import gate is expected. Do not modify its legacy data merely to bypass that state.
- [ ] **HTTPS and HTTP redirect:** run both actual production configurations with secure cookies, preserved Host/HTTPS scheme, JSON API errors/private-log denial and all five native oversized-upload routes. The last separate HTTPS fixture stopped on an assumed 307 for a trailing-slash login route before upload checks; diagnose the actual router status/Location instead of treating that assumption as a confirmed TLS bug. Those temporary resources were removed.
- [ ] **Final broad details:** repeat the populated detail/statistics/admin/OIDC/theme matrix after adapting renamed Media Collections expectations. The 352-case WebKit detail review passed at `2e3d5de0`; final main has newer scoped collections/search behavior. Historical save/startup/welcome/search/appearance and PWA evidence is retained, with exact source heads.
- [ ] **Live metadata providers:** exercise current real configured providers for live Find, explicit artwork search and manual-field locking. Final UI checks use deterministic intercepted provider responses; backend regressions do not certify every remote provider's current service.
- [ ] **Physical devices:** verify Safari browser chrome/safe areas, actual PWA OS installation and browser-reserved Alt shortcuts. Automated WebKit and prompt-event boundary checks are already accepted, but do not emulate every physical device/OS interaction.

## Reproduction

Use an owned disposable production deployment. Keep the core browser fixture's
plugin inventory empty; use a separate paired fixture for installed native
plugin checks. Never reconcile a populated runtime against an empty host.

The public harness accepts `UI_REVIEW_PRODUCTION_ORIGIN`,
`UI_REVIEW_HOST_HEAD`, `UI_REVIEW_BROWSER=chromium|webkit` and review-account
credentials through the environment. Do not commit credentials, cookie files
or private server logs.

```sh
node tools/check_ui_redevelopment.mjs /path/to/unnamed_tracking_app_plugins /path/to/evidence http://127.0.0.1:PORT editors
node tools/check_ui_redevelopment.mjs /path/to/unnamed_tracking_app_plugins /path/to/evidence http://127.0.0.1:PORT details
node tools/check_native_plugin_ui.mjs /path/to/unnamed_tracking_app_plugins /path/to/evidence http://127.0.0.1:PORT /private/admin-cookies.json
```

After fixes, record the exact host/runtime/package heads, role/theme/width,
assertions and screenshots. Convert confirmed product failures into issues;
keep harness assumptions and unfinished verification in this checklist.

## Deliberate boundaries

New plugins target v1.1; limited legacy compatibility is for shipped examples
and already-installed old plugins. Optional reduced-isolation acknowledgement
does not replace gateway configuration. Themes remain basic reviewed CSS
packages with manual updates. The Playnite preconfigured-download investigation
is documented in [Playnite integration](../integrations/playnite.md): full
preconfiguration needs extension bootstrap and private credential delivery and
was not added as an unreviewed authentication path.
