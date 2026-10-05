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
companion `examples/theme-palettes` source includes Blue Hour and Purple Blocks.
Its optional native permission demonstrates a stylesheet that changes component
shapes as well as colours.

## Stylesheet overrides

Plugins can declare `native_frontend.styles` and receive the separate privileged
`frontend.native` permission to load CSS into the host. This permission also
allows native JavaScript access to the signed-in application; it is never implied
by the palette permission. Existing native activation and deactivation remove
styles when the installation is disabled, revoked, quarantined or uninstalled.

For an optional theme, scope selectors to
`[data-plugin-theme="plugin:<plugin_id>:<theme_id>"]`. The host applies this
attribute to the document root only when both saved palette modes match that
active, approved contribution. It also applies the scope to the settings preview.
Switching palettes or editing colours removes the scope while preserving the
personal colour copy. This lets multiple installed themes coexist.

Override public `--ui-*` tokens first, then host selectors when needed. Test
focus, contrast, touch targets and small screens. Purple Blocks demonstrates
square controls, bold card borders and a purple palette in both modes without
replacing the application or importing its private source.

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

The shared helper also reports its intrinsic body height through `plugin.resize`.
The host accepts this only from that frame's window and clamps the requested
height to 320–2400 pixels. Longer content retains its internal scrolling. This
lets phone readers reveal their controls without a fixed desktop-sized frame.

Snapshots contain `api_contract_version: "1.1.0"`, `mode`, `high_contrast`,
`reduce_motion` and an allowlist of cosmetic `tokens`. They contain no account
identifiers, authentication, library content, secrets or other preferences.
The opaque `allow-scripts` sandbox and independently authorized actions remain
in force. Document paper, images and other rendered media may retain their
content colors while the reader's controls follow the host palette.
