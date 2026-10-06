# Plugin Home widgets

Plugin UI/API **1.1.0** adds `home_widgets` to `ui.json`. The installation must
declare and receive `frontend.home.widgets` v1. This permission registers optional
content; it does not grant library access, native JavaScript or other UI scopes.
The user selects and orders widgets through **Home → Customize Home**.

```json
{
  "id": "library-glance",
  "title": "Library glance",
  "description": "A few picks from your personal game library.",
  "page_id": "library-glance",
  "mobile_page_id": "library-glance-mobile",
  "order": 0,
  "configuration": [{
    "id": "limit", "label": "Number of games", "type": "number",
    "required": true, "default": 4,
    "validation": {"minimum": 1, "maximum": 8}
  }]
}
```

This is a single registration inside the `home_widgets` array. Both page IDs must
reference declared `pages`; include those pages in the manifest's `ui.pages`.
The document and manifest both declare `api_contract_version: "1.1.0"`.
IDs are unique within the plugin and cannot collide with a `home.after-widgets`
extension ID. Existing permitted Home extensions remain selectable widgets.

## Personal options and responsive rendering

Widget options reuse the public declarative field definitions. The host renders
an accessible Options dialog, validates declared types/options/bounds and saves
to the authenticated account's existing preferences. They are separate from
installation-wide plugin settings. No secret or password field is permitted.

Configuration supports up to 16 fields per widget and 32 retained configurations.
Values are bounded strings (2048 characters), finite numbers and bounded lists of
strings. The host discards undeclared or invalid saved fields when passing values
to the UI and uses declared defaults where available. Removed fields may remain
in stored preferences until the user saves the current options.

Native page components receive a reactive `widgetConfig` prop and the existing
`context` prop. Declarative actions receive `_widget_configuration` as JSON in
their ordinary action values. Treat those values as user input. The backend
supplies the authoritative authenticated user in `_plugin_context` and discards
any caller-provided replacement for that context. At widths up to 760px the host
mounts `mobile_page_id`, if present. Otherwise the ordinary page follows the shared
responsive primitives. Resizing changes the page and cleans up the old component.

## Permission and lifecycle behavior

The host filters registrations by effective grants before returning UI documents
and checks again in its frontend registry. `visibility.admin_only` excludes the
widget from member choices and Home rendering. Disable, incompatibility,
uninstall or revoked access withdraws live content. Selection and configuration
remain personal and retained; unavailable selections show a host placeholder.
Account changes close an open Options dialog and invalidate queued saves.

Native widgets additionally need the existing privileged `frontend.native` grant.
They use the public Vue/native SDK and inherit the host's semantic CSS variables.
Native activation or rendering failures stay inside the contribution boundary.
They must dispose timers/listeners through component cleanup or `onCleanup`.

The companion `examples/home-widgets` source demonstrates Library glance with a
separate phone layout and an **Embedded media demo widget**. A source declaration
alone does not establish package trust. Build, sign and test through the ordinary
verified `.utp` installation flow. Embedded media must not enter PR screenshots,
recordings, thumbnails or previews.
