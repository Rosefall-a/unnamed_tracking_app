# Plugin UI/API v1.1 migration

## Version diagnostics

Plugin Manager's platform information reports the host API contract, SDK and
application compatibility version alongside the runtime's reported versions and
gateway protocol. Missing, mismatched or unavailable runtime information has a
specific health message. Plugin details and install consent show the release's
API contract and required SDK/application ranges with the actual host values.
An incompatible package remains inspectable. A prominent “Unable to install”
notice and disabled button identify the blocker; each failed API, SDK and
application requirement is highlighted with its required and actual values.
The application compatibility version is a range target, separate from package
release versions. A broad SDK range does not establish v1.1 UI migration.

New plugins require an explicit **1.1.0** plugin contract. The HTTP and
line-protocol wire major remains `v1`, and the archive remains `.utp`. A plugin's
release `version` is independent of its UI/API contract version.

## Declare and migrate both documents

Use the following fields in `manifest.json`:

```json
{
  "manifest_version": 1,
  "api_contract_version": "1.1.0",
  "sdk_version_range": "^1.1.0"
}
```

Declare `"api_contract_version": "1.1.0"` in `ui.json` as well, while retaining
`"schema_version": "v1"`. The two contract declarations must match. These are
partial examples; all existing identity, capabilities, permissions, handlers,
entrypoints and integrity fields remain required by their respective schemas.

An absent declaration defaults to **1.0.0**. A broad range such as `*` or
`^1.0.0` does not certify migration. Legacy manifest alias conversion does not
upgrade the contract. Review and test the actual UI and backend against the new
host before changing the declaration; a marker alone does not make the UI fit
the new design system.

## Installed legacy plugins

Shipped historical examples and plugins already installed on a server may use
**limited v1.0 compatibility**. Plugin Manager warns during installation and in
the installed release's details that the package targets the old UI and some
features or page styling may be limited. Eligibility uses a reviewed list of
shipped IDs or an existing installation identity, never an `example.*` prefix.
Other newly installed v1.0 plugins must migrate before installation.

The adapter supports existing backend features, declarative settings and
sandboxed embedded pages. New native UI, theme/shortcut contributions, home
widget registrations and built-in section placement require a v1.1 update.
Legacy SDK ranges that explicitly support 1.0.0 can use the limited SDK adapter;
application ranges and future SDK requirements are still enforced. A v1.1
plugin never becomes compatible with an old v1.0 host through this adapter.

Installation identity, stored data, settings and recorded permission grants are
retained. The original enablement preference is recorded separately from
effective execution. A verified, compatible update can reactivate an installation
whose enablement was requested, using the normal consent and transaction flow.
Disabled installations remain disabled. Unchanged grants do not require new
consent; additional permissions still require approval.

Package verification, publisher trust, explicit permission consent and elevated
reauthentication remain unchanged. Disabled plugins remain disabled, and
uninstall removes the previous installation identity. Eligible historical
releases can be selected for rollback with the same verification and consent
flow. Installing an older catalogue release pins it and disables automatic
updates until the administrator resumes them.

## Verify an update

Keep plugin IDs stable, build a new release through the companion repository's
existing builder, and preserve published archives and release history. The new
contract declaration is included in the signed manifest binding. Digest,
signature, publisher, permission, storage and isolation checks still apply.

Test installation, retained data, restart, denied new permissions, update failure,
rollback and uninstall through the real host/runtime. Review desktop, phone,
light and dark UI separately. See [manifest compatibility](plugin-manifest.md),
[UI protocol](plugin-ui.md) and [integration verification](plugin-integration-verification.md).

The host CI also runs `tools/check_plugin_contract_upgrade.py` against the actual
companion repository. It verifies a published signed Playtime Report archive,
starts its real historical worker to simulate the predecessor host, then checks
that the current registry stops it and refuses restart. It rebuilds the migrated
source through the companion builder with a disposable signing identity and
verifies that the new worker runs with the original installation identity,
settings and stored report. The published archive remains byte-identical.

Run this process-mode acceptance only in a disposable environment:

```sh
NONBUBBLE_ENV=true python tools/check_plugin_contract_upgrade.py \
  --plugins-root /path/to/unnamed_tracking_app_plugins \
  --work-root /tmp/contract-upgrade-acceptance
```

The work directory must not already exist. The check creates no browser or media
captures. Strict sandbox execution is verified separately by the official
Jellyfin acceptance runner.
