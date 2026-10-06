# App branding

Open **Settings → Administration → App branding** to set the server's public application name, navigation logo and browser icon. Only administrators can change these values; members do not see these controls. The name and images appear before login and must contain only public information.

Names contain 1–64 printable characters. Saving **Archive** restores the default name. Choose a static PNG, JPEG or WebP up to 2 MB, 4096 pixels per side and 16 megapixels. The server decodes each image, removes metadata and saves a PNG no larger than 512 pixels. SVG and animated images are rejected. Uploads take effect after a successful save; an error preserves the current branding and allows a retry.

The logo appears in navigation, sign-in and setup. A separate browser icon takes precedence in browser tabs; otherwise the app logo is used. Removing both restores the built-in icon. Image URLs include a content revision so browsers do not keep showing an earlier image after it changes. Previously issued URLs stop serving the removed or replaced image.

When a healthy PWA provider has its site-wide permission, a custom name also appears in the installed app's manifest. Its icons use the custom logo, with the browser icon as a fallback, centered inside the maskable safe area. Branding changes update the PWA cache generation. Revoking, disabling or uninstalling the provider still withdraws its manifest and icons; branding does not enable PWA installation by itself. Existing OS launchers may refresh their labels and icons on a browser-managed schedule.

Branding is stored in the existing deployment settings row and follows database backups. Migration `c2a9e6f4b801` adds three nullable columns after the published merge revision, preserving provider configuration and personal preferences. Existing installations retain their configured integrations and receive the default identity until an administrator changes it.

Your theme and completed-game badges remain personal. Use **Preferences → Appearance** for those account choices.
