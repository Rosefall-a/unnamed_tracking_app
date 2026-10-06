# Custom frontend sandbox design

The declarative Plugin UI v1 host is the default. Complex interfaces can declare a static `frontend.entry` and run on the plugin's dedicated page in a sandboxed iframe.

## Security model

Custom frontend code does not execute inside the core Vue application. The iframe uses `sandbox="allow-scripts"` without `allow-same-origin`, and the host accepts messages only from that iframe's `contentWindow`.

The bridge supports basic context, ordinary settings, write-only secrets, and declared actions. CSP denies direct network connections and object embedding; PDF viewing is limited to blob-backed frames created from host-approved document bytes. The host does not expose environment values, credentials, DOM access, or a second permission system. Every bridge operation that reaches privileged host data is authorized again at the backend gateway.

Sandboxed and native frontends are distinct declarations and a plugin may declare both. `frontend.entry` remains the ordinary iframe model and does not require native execution. `native_frontend` represents trusted Vue/JavaScript/CSS integration and requires the explicit critical-risk `frontend.native` capability. Native loading is not enabled by merely declaring the bundle.

## Lifecycle

The runtime verifies package integrity and compatibility before the browser loads
custom code. Disabling, uninstalling, updating, or revoking permission refreshes
the host contribution registry. Sandboxed frontends cannot mutate the host DOM or
mount themselves into native host extension slots. A separately declared native
bundle can fill those slots only after the backend confirms `frontend.native`;
native activation does not change the iframe sandbox or bridge.

See [Plugin UI Protocol](plugin-ui.md) for the native renderer and [Plugin API v1](plugin-api-v1.md) for the gateway contract.

## Navigation while a plugin frame has focus

The public appearance snapshot includes `navigation_shortcuts`, the single-letter keys currently supported by the host's Alt navigation. The shared frontend SDK forwards these keys through `plugin.shortcut` with `{ "key": "g" }`, for example. It ignores editing controls, composition, repeats, AltGraph, conflicting modifiers and already-handled events. Bindings come from the same host table used by tooltips and keyboard help; plugins do not maintain a separate route list.

The host accepts requests only from that contribution's own opaque frame and only for mapped navigation keys. It does not accept arbitrary paths, URLs or privileged operations. The shared host keyboard handler retains its open-dialog and command-palette guards. Existing frontend action/capability checks and the iframe sandbox are unchanged.

The additive `global_shortcuts` list advertises `help` (`?`) and `search` (Ctrl/Cmd+K). The SDK forwards those exact identifiers through the same `plugin.shortcut` method, so native host help/search remain available from inside the frame. Older snapshots without this list do not forward global dialog keys. Editing and modifier guards still apply.
