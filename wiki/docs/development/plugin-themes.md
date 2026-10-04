# Plugin palettes and appearance

Plugin UI/API **1.1.0** offers named personal palettes through `ui.json`'s
`themes` array. Declare and receive `frontend.themes` v1. This independent,
low-risk permission does not grant native code, account data, arbitrary CSS or
page replacement. The host validates every palette before offering it in
**Preferences → Appearance & interface → Color palette**.

Each theme has a plugin-local `id`, `label`, optional `description` and `order`,
and `colors.light` / `colors.dark`. Both modes must contain exactly these roles:
`background`, `surface`, `surface_alt`, `text`, `muted`, `accent`, `success`,
`warning`, `error`, `info` and `purple`. Values are six-digit hexadecimal colors.
The host derives borders, selected surfaces, foregrounds and interaction states.
Documents allow up to 32 themes with unique IDs; unknown roles are rejected.

Applying a plugin palette saves a **personal custom-color copy** in the account's
existing preferences. It remains editable, exportable and available after the
plugin is disabled, revoked or uninstalled. Revocation removes its selectable
source; it does not overwrite saved personal colors. Contrast advice never
blocks applying a valid palette. System mode still follows the device. The
companion `examples/theme-palettes` source demonstrates a palette-only plugin
with no privileged native code or data permissions.

## Native components

Native components inherit the host's semantic `--ui-*` CSS variables. Use those
roles for backgrounds, text, status, focus, controls and spacing rather than
literal application colors. The public SDK also exposes `host.appearance()` and
`host.onAppearanceChange(callback)`. The latter returns an unsubscribe function
and is automatically disconnected when the plugin deactivates. Page-local
listeners should still be disposed through Vue's unmount lifecycle.

## Sandboxed components

Opaque iframe frontends request `plugin.theme` through the existing
`plugin-api-request` / `plugin-api-response` bridge. `plugin.context` includes
the same `appearance` snapshot. The host sends `plugin-appearance-changed`
messages when root appearance changes and after iframe load. The companion
SDK's `frontend_appearance.js` applies these public tokens and accepts messages
only from its parent. Its CSS supplies semantic fallback roles and touch targets;
the package builder includes both files for bundled frontends.

Snapshots contain `api_contract_version: "1.1.0"`, `mode`, `high_contrast`,
`reduce_motion` and an allowlist of cosmetic `tokens`. They contain no account
identifiers, authentication, library content, secrets or other preferences.
The opaque `allow-scripts` sandbox and independently authorized actions remain
in force. Document paper, images and other rendered media may retain their
content colors while the reader's controls follow the host palette.
