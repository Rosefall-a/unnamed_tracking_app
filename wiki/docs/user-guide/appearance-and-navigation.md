# Appearance and navigation

The application uses Archive's desktop structure with Pocket's floating navigation and rounded phone controls. Desktop, tablet and phone share routes and features, with different navigation layouts.

## Navigation

On a desktop, the navigation pane stays visible. On a tablet, **Auto** uses an icon rail; its menu button expands the labels. On a phone, the rounded bottom bar offers Home, Library, Media and More. Library and Media open their groups in the full menu. More provides the rest of the library, tools, settings and active plugin links.

The phone menu contains keyboard focus, closes with Escape or its close button, and returns focus to the opening control. Desktop navigation can be resized by dragging its right edge, or focusing that edge and using Left/Right; Home/End choose its minimum/maximum width. Double-click resets the width. Navigation remembers the width and the Auto, Overlay, Pinned or Icon rail choice on this device. Phones always use the bottom bar regardless of that desktop choice.

Disabled, incompatible or uninstalled plugins do not contribute navigation. Plugin links and actions retain their original capability and administrator checks.

## Settings areas

- **Preferences** contains a combined Appearance & interface page, notifications, calendar, shortcuts and library settings.
- **Account** contains profile/password, connections and API keys.
- **Administration** contains server management, [app branding](../administration/branding.md), plugins, background tasks and storage/usage. Only administrators see this area. Its banner explains that changes affect everyone on the server.

Settings starts with grouped links. On desktop a section keeps its area navigation beside the form; on a phone it opens as a separate screen, with a back link to its area. Existing `/settings?section=…` links continue to work, including the older aliases for library, metadata and administration tabs. The unfinished Logs entry is not offered.

## Personal appearance

Open **Preferences → Appearance & interface**. Theme and layout, navigation and library defaults, and completed-game badges share this page. Existing `section=interface` and `section=appearance` links both open it.

The first time an account opens this interface, **Make yourself at home** offers theme, palette, spacing, motion and contrast choices with a live menu/card preview. **Save & continue** saves those choices and completion to that account. Keeping the displayed defaults is also a valid choice. If saving fails, the dialog keeps your selections and offers another attempt; it does not mark the welcome complete. You can revisit all appearance controls in Preferences.

- **Theme:** System, Light or Dark. System follows changes to the device appearance.
- **Palette:** Orange, Green or Custom. Each palette has separate light and dark colors. The custom editor controls eleven semantic color roles and previews menus, cards, dialogs and controls before you select **Apply palette**. Both color sets are saved together. Low-contrast pairs show an optional advisory; you can apply any valid six-digit colors. The preview starts in the currently displayed theme and follows later app or System theme changes; you can switch it manually. **Download palette** shares both color sets as a JSON file. **Import palette** loads a shared file into the preview; choose **Apply palette** to save it. Invalid or oversized files leave your saved colors intact.
- **Density:** Comfortable or Compact. Compact reduces spacing while retaining phone touch targets.
- **Reduce motion:** disables decorative transitions. The device's reduced-motion setting is always respected.
- **Higher contrast:** strengthens text, boundaries and keyboard focus.
- **Navigation & library defaults:** choose the sidebar, default Games view and sorting on this device.
- **Completed game badges:** choose the style, color, placement and optional image for your completed-game cards.

Theme, palette, density, contrast, motion and badges belong to your account. Badge choices remain personal and existing saved values are preserved. Appearance changes save as you make them; badge customization keeps its explicit Save button. A failed save displays an error and restores the previous appearance. Signing out discards queued preference writes and cached badges so they cannot affect the next signed-in account. A late badge response from the previous account is ignored.

This browser saves a cosmetic copy of theme, palette, spacing, style, motion and contrast in a same-site cookie so public sign-in, local sign-in fallback and SSO redirects keep your appearance after sign-out or reload. HTTPS adds the Secure cookie flag. The cookie expires after one year and contains no account identity, credentials, welcome-completion state or library records. A cosmetic local-storage copy continues to support the neutral PWA offline page. Signing into another account applies that account's saved appearance. Restricted browser storage does not prevent server preferences from working. Browser bars follow the active page background.

Navigation, Settings, [Home](home.md), games, collections, cards, sets, media and statistics use the shared appearance system. The remaining plugin migration is tracked in the [development checkpoint](../development/ui-redevelopment.md). The preserved [interactive concept gallery](../assets/ui-redevelopment/concepts.html) remains available as a reference; its illustrative screens are not product features or additional selectable styles.


## Search and keyboard help

Open **Search library** from the menu, or press **Ctrl/Cmd + K**, to find games, movies, TV shows, anime, collections, goals, settings and active plugin pages. A failed provider leaves available results visible and offers Retry. Search and settings results respect your account's permissions.

Press **?** to show keyboard help. The current page's section comes first and opens automatically; expand or collapse other sections as needed. The same help appears under Settings → Keyboard Shortcuts. **/** focuses the current page's search, or opens Search library when there is no local search. **n** opens the current page's create control when available. **Alt + a letter** navigates globally; hover navigation links to see their keys. The full mappings are in help. Shortcuts pause while you type or use a dialog.
