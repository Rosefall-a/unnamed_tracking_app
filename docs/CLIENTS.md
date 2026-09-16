# Client applications

All clients connect to the same hosted frontend/API origin. Enter `http://` explicitly for a trusted local HTTP deployment and `https://` for TLS. None of the clients bypasses certificate validation.

## Choosing a client

| Client | Platforms | Update model | Notes |
| --- | --- | --- | --- |
| Progressive Web App | Android, Windows, Linux, macOS | Hosted Vue UI updates immediately | Simplest installation; requires a browser with PWA support |
| Tracking Web APK | Android 10+ | Hosted Vue UI updates immediately | WebView container with upload/download support |
| Tracking Native APK | Android 10+ | Updated through new APK releases | Native Material 3 UI and system-browser OIDC |
| Tracking Windows Web | Windows 10+ | Hosted Vue UI updates immediately | WebView2 ZIP/MSIX; requires the Evergreen WebView2 runtime |

The PWA caches only static application assets. API responses, authentication endpoints, and personal library data are never written to Cache Storage. Offline mode provides a reconnect screen rather than a stale or incomplete library.

## Downloads

Use the repository's **Releases** page for normal installation. Each tagged release contains stable filenames:

- `tracking-web.apk`
- `tracking-native.apk`
- `tracking-windows-web.zip`
- `tracking-windows-web.msix`
- `SHA256SUMS.txt`

For an unmerged pull request, open its Checks page and select the `tracking-web-apk`, `tracking-native-apk`, or `tracking-windows-web` artifact. These are development builds and expire according to GitHub's artifact retention setting.

## Installing the PWA

Serve the application through HTTPS, open it in Chrome or Edge, and select **Install Archive** from the browser's application/install menu. Localhost is treated as a secure development origin. The service worker is registered only in production builds.

## Release automation

Pushing a `v*` tag starts `.github/workflows/client-release.yml`. The workflow tests the clients, creates signed installable packages, writes SHA-256 checksums, and attaches the results to a GitHub Release.

Configure these encrypted repository secrets before creating a release tag:

- Android: `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`
- Windows: `WINDOWS_CERTIFICATE_BASE64`, `WINDOWS_CERTIFICATE_PASSWORD`

The Windows certificate subject must match `CN=ArchiveTracking` in `src/windowsapp/packaging/AppxManifest.xml`. Production publishers should replace both values together with their real code-signing identity.

## Keeping clients aligned

The PWA, Tracking Web APK, and Windows WebView2 client all render the hosted Vue application, so normal Vue changes require no client release. Tracking Native has its own UI and must be updated when an API or user workflow changes. Shared API behaviour is protected by backend tests, Android URL/auth tests, and the Windows `Tracking.Core` contract tests.

When adding an API feature, update the OpenAPI contract and web UI first, then decide whether the native Android experience needs a dedicated screen. Keep unsupported native workflows visible in the tracking issue rather than silently presenting incomplete data.
