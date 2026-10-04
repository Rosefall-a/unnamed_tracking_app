# Plugin UI/API v1.1 migration

The redesigned host requires an explicit **1.1.0** plugin contract. The HTTP and
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

An already-installed v1.0 plugin becomes **incompatible**. The runtime stops its
workers and refuses startup, bootstrap, actions, routes and gateway requests.
The host also refuses contributions, assets and PWA publication even if a stale
runtime response claims the installation is running. Core pages remain usable.

Installation identity, stored data, settings and recorded permission grants are
retained. The original enablement preference is recorded separately from
effective execution. A verified, compatible update can reactivate an installation
whose enablement was requested, using the normal consent and transaction flow.
Disabled installations remain disabled. Unchanged grants do not require new
consent; additional permissions still require approval.

Legacy packages remain inspectable and signature-verified for diagnosis and
history. The install preview reports their contract and an actionable reason,
but they cannot be installed, enabled or selected as executable rollback targets
on this host. An administrator cannot override the contract boundary by accepting
an untrusted-package warning or changing the SDK environment setting.

## Verify an update

Keep plugin IDs stable, build a new release through the companion repository's
existing builder, and preserve published archives and release history. The new
contract declaration is included in the signed manifest binding. Digest,
signature, publisher, permission, storage and isolation checks still apply.

Test installation, retained data, restart, denied new permissions, update failure,
rollback and uninstall through the real host/runtime. Review desktop, phone,
light and dark UI separately. See [manifest compatibility](plugin-manifest.md),
[UI protocol](plugin-ui.md) and [integration verification](plugin-integration-verification.md).
