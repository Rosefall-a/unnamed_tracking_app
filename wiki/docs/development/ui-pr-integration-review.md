# UI redevelopment: current open-PR integration review

Snapshot: 2026-10-06. Main `6244677` is integrated through Plugin Manager
`9a3964d` into native UI `b76811db`, with presentation follow-up
`e01f28c3`. Both required branch relationships are clean and preserve the
redesigned navigation, theme/dialog controls and native plugin boundaries.

The former removal of core Cards/Sets/Bounties is integrated with the agreed
official Collector's Archive replacement. Main's game/media/detail,
metadata/filter, proxy/password/startup and latest #423 refinements are retained.
Older tables documenting those merged PRs as open alternatives are superseded.

The [machine-readable audit](../assets/ui-redevelopment/merge-readiness/open-pr-integration-audit.json)
records exact remaining PR heads and merge-tree conflicts. This is a review of
integration feasibility, not an instruction to merge unrelated proposals.

| Open PR | Audited head | Textual result | Integration boundary |
| --- | --- | --- | --- |
| [#399: Pelican integration discovery](https://github.com/Rosefall-a/unnamed_tracking_app/pull/399) | `8253de92` | Clean, no overlapping application changes | Documentation/experiments only. Its branch already incorporates the former foundation head; future live Pelican features still need explicit public contracts. |
| [#250: Pylint 10/10 policy](https://github.com/Rosefall-a/unnamed_tracking_app/pull/250) | `f95ba85e` | 40 conflicting files, 78 shared changes | Rework against current auth/plugin/migration modules. Current configured Pylint is 9.17/10 and passes the existing 9.0 threshold; it does not meet this separate proposed policy. |
| [#249: isolated wiki container](https://github.com/Rosefall-a/unnamed_tracking_app/pull/249) | `cd0b6bc9` | Two conflicts | Reconcile .gitignore/MkDocs around current plugin/theme/UI evidence and preserve isolated documentation setup. |
| [#232: explicit title write protection](https://github.com/Rosefall-a/unnamed_tracking_app/pull/232) | `470219ff` | Clean, no overlapping changes | Verify its title-protection intent alongside current metadata locking and native repull controls. |

No unrelated open PR was modified or merged. A clean textual merge still needs
behavioral validation. Resolve overlapping changes against current components;
do not replace native UI or security modules with whole older files.

## Coordinated review order

1. Host Plugin Manager [#305](https://github.com/Rosefall-a/unnamed_tracking_app/pull/305), then native UI [#398](https://github.com/Rosefall-a/unnamed_tracking_app/pull/398).
2. Maintained plugins [#39](https://github.com/Rosefall-a/unnamed_tracking_app_plugins/pull/39), canonical PWA [#4](https://github.com/Rosefall-a/unnamed-tracking-mobile-app/pull/4), template [#2](https://github.com/Rosefall-a/plugins-template/pull/2) and themes [#1](https://github.com/Rosefall-a/unnamed_tracking_app_themes/pull/1), with the documented v1.1 host/asset dependencies.

Current source/production results are in [final integration](final-main-ui-integration.md).
The remaining acceptance list is [exported separately](ui-merge-checklist.md),
and the observed Archive re-enable limitation is [#430](https://github.com/Rosefall-a/unnamed_tracking_app/issues/430).
