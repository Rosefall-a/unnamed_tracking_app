# Appearance and navigation

The application uses Archive's desktop structure with Pocket's floating navigation and rounded phone controls. Desktop, tablet and phone share routes and features, with different navigation layouts.

## Navigation

On a desktop, the navigation pane stays visible. On a tablet, **Auto** uses an icon rail; its menu button expands the labels. On a phone, the rounded bottom bar offers Home, Library, Media and More. Library and Media open their groups in the full menu. More provides the rest of the library, tools, settings and active plugin links.

The phone menu contains keyboard focus, closes with Escape or its close button, and returns focus to the opening control. Desktop navigation can be resized by dragging its right edge, or focusing that edge and using Left/Right; Home/End choose its minimum/maximum width. Double-click resets the width. Navigation remembers the width and the Auto, Overlay, Pinned or Icon rail choice on this device. Phones always use the bottom bar regardless of that desktop choice.

Disabled, incompatible or uninstalled plugins do not contribute navigation. Plugin links and actions retain their original capability and administrator checks.

## Settings areas

- **Preferences** contains appearance, interface defaults, notifications, calendar, shortcuts and library settings.
- **Account** contains profile/password, connections and API keys.
- **Administration** contains server management, [app branding](../administration/branding.md), plugins, background tasks and storage/usage. Only administrators see this area. Its banner explains that changes affect everyone on the server.

Settings starts with grouped links. On desktop a section keeps its area navigation beside the form; on a phone it opens as a separate screen, with a back link to its area. Existing `/settings?section=…` links continue to work, including the older aliases for library, metadata and administration tabs. The unfinished Logs entry is not offered.

## Personal appearance

Open **Preferences → Appearance**:

- **Theme:** System, Light or Dark. System follows changes to the device appearance.
- **Palette:** Orange, Green or Custom. Each palette has separate light and dark colors. The custom editor controls eleven semantic color roles and previews menus, cards, dialogs and controls before you select **Apply palette**. Both color sets are saved together. The editor blocks unreadable text/background combinations; only plain six-digit colors are accepted.
- **Density:** Comfortable or Compact. Compact reduces spacing while retaining phone touch targets.
- **Reduce motion:** disables decorative transitions. The device's reduced-motion setting is always respected.
- **Higher contrast:** strengthens text, boundaries and keyboard focus.
- **Completed game badges:** choose the style, color, placement and optional image for your completed-game cards.

These choices belong to your account. Badge choices remain personal and existing saved values are preserved. Appearance changes save as you make them; badge customization keeps its explicit Save button. A failed save displays an error and restores the previous appearance. Signing out discards queued preference writes and cached badges so they cannot affect the next signed-in account. A late badge response from the previous account is ignored.

This device keeps only a cosmetic copy of theme, palette and contrast settings so public sign-in, local sign-in fallback and SSO redirects use the same colors after sign-out or reload. It contains no account identity, credentials or library records. Signing into another account applies that account's saved appearance. Browser bars follow the active page background.

Navigation, Settings, [Home](home.md), games, collections, cards, sets, media and statistics use the shared appearance system. The remaining plugin migration is tracked in the [development checkpoint](../development/ui-redevelopment.md). The preserved [interactive concept gallery](../assets/ui-redevelopment/concepts.html) remains available as a reference; its illustrative screens are not product features or additional selectable styles.
