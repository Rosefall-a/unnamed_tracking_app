# Installed themes

Administrators install `.utt` CSS packages in **Settings → Administration →
Themes**. Drop a package onto the install box or choose **Install theme**, review
its publisher, release and supported color modes, and install it. Uploading the
same ID replaces that theme. Updates are manual.

Enable or disable each installed theme, remove it, or choose an enabled theme as
the **Server default**. The server default also applies to sign-in and OIDC
pages when the browser has no personal theme choice. Disabling or removing the
default returns the server to the native interface.

Users select **Server default**, **Native interface** or an enabled installed
theme in **Preferences → Appearance & interface → Interface theme**. The menu
preview uses the current theme. **Save theme choices to** selects an account
preference or a cosmetic browser cookie for the theme, light/dark/system mode,
palette and higher-contrast choice. Browser choices do not update the account;
layout preferences continue to follow the account. Missing or unsupported themes
fall back to the native interface while retaining the personal selection.

Themes contain CSS, images, fonts and documentation. They have no plugin worker,
SDK permissions or automatic-update settings. CSS can change the complete
interface, including the sidebar and native plugin components. Opaque iframe
plugins retain their isolation and receive the host's public appearance tokens.

The [themes repository](https://github.com/Rosefall-a/unnamed_tracking_app_themes)
contains an official Forest theme and a Purple Blocks example, a deterministic
package builder, package-format documentation and an `unsigned-dist` CI artifact
on every branch. Collection labels describe the package's declared collection;
they are not publisher signature verification.

Packages and the server default persist under `/data/themes`. A test/deployment
override can use `THEME_STORE_PATH`. Keep this directory with the app's persistent
data. The host validates bounded ZIP contents before installing and exposes only
enabled current assets under digest-specific public URLs, allowing appearance
to load before authentication.

Breaking changes: None. Executable theme plugins and their palette permissions
continue to work independently.
