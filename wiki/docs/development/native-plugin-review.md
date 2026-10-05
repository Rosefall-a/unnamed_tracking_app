# Native plugin layout review

The current unsigned Jellyfin and theme packages were installed through the
public package review and consent flow in an isolated test server. The native
Document Browser settings came from the validated distribution artifact.

Loaded Jellyfin server and account settings and Document Browser controls were
checked at 320, 390, 1440 and 1920 pixels in light and dark modes. The checks wait
for configuration to load, verify administrator access, and reject horizontal
overflow. Official Jellyfin entries are direct items under **Server management**,
**Account**, and the **Media** sidebar heading.

![Loaded Jellyfin server settings](../assets/ui-redevelopment/jellyfin-admin-loaded-1440-light.png)

![Jellyfin accounts on a phone](../assets/ui-redevelopment/jellyfin-accounts-loaded-390-dark.png)

![Loaded Document Browser settings](../assets/ui-redevelopment/document-browser-settings-loaded-1440-light.png)

![Document Browser settings on a phone](../assets/ui-redevelopment/document-browser-settings-loaded-390-dark.png)

Purple Blocks demonstrates the granted global stylesheet capability: it squares
the sidebar, account controls, settings navigation, phone tabs and plugin forms.
Switching to Blue Hour releases its shape overrides.

![Purple Blocks across the desktop shell and native plugin](../assets/ui-redevelopment/purple-blocks-native-shell-1440-light.png)

![Purple Blocks across the phone shell and native plugin](../assets/ui-redevelopment/purple-blocks-native-shell-390-dark.png)

The live Jellyfin check exercised connection, discovery and username/password
sign-in without a manually supplied UUID. Synchronization was disabled, the
media-write permission was denied, and the processed-media count stayed zero.
Test credentials were removed from plugin storage. The public screenshots use
an empty disposable configuration and contain no live server information.

These checks cover this milestone. Final production, permission lifecycle and
remaining plugin integration checks are tracked separately.
