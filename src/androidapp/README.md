# Android apps

This project intentionally ships two co-installable Android 10+ applications:

| APK | App name | Package | Best for |
| --- | --- | --- | --- |
| `tracking-web.apk` | Tracking Web | `com.rosefall.tracker.webapp` | Complete Vue feature parity and automatic UI updates |
| `tracking-native.apk` | Tracking Native | `com.rosefall.tracker.nativeapp` | Native Material 3 navigation and Android behaviour |

Debug builds append `.debug` to the package ID so they do not replace signed release installations.

## User setup

1. Download either or both APKs from the repository's latest GitHub Release.
2. Allow installation from the browser or file manager when Android asks.
3. Install the APK and enter the full address of the tracking frontend.
4. Sign in with local credentials or, in Tracking Native, select a configured SSO provider.

The native app retains the server's `HttpOnly` session cookie in a private persistent cookie store and sends it only to matching server URLs. The web app uses Android WebView's first-party cookie store.

Use HTTPS whenever the server is reachable outside a trusted LAN. Cleartext HTTP
is enabled only to support local self-hosted addresses. The app does not bypass
certificate failures.

Always include `http://` or `https://` when the server's protocol is known. When
omitted, private LAN and emulator addresses default to HTTP while public hostnames
default to HTTPS. TLS certificate verification is never bypassed.

## Native OIDC

Tracking Native opens OIDC in the system browser. It creates a high-entropy PKCE verifier locally, sends only its SHA-256 challenge to the backend, and accepts a two-minute one-use handoff code at `tracking-native://oidc/callback`. The server creates the normal `HttpOnly` session cookie only after the app proves possession of the verifier. OIDC access tokens and application session tokens are never placed in the app callback URL.

The backend database must be migrated to the current Alembic head before using native OIDC.

## Development

Open `src/androidapp` in Android Studio, allow Gradle sync to finish, and run the
either the `app` (native) or `webapp` configuration. The default server is blank so the first-launch setup is shown. To bake a default into local builds:

```properties
# ~/.gradle/gradle.properties (do not commit real deployment URLs)
trackingAppServerUrl=https://tracker.example.com
```

Command-line checks, from this directory with Gradle 8.9 installed:

```bash
gradle testDebugUnitTest lintDebug assembleDebug
gradle :app:connectedDebugAndroidTest  # with an emulator/device attached
```

The Gradle project contains:

- `app` — native Compose UI, OkHttp API client, private cookie jar, and system-browser OIDC.
- `webapp` — title-bar-free WebView client with uploads, authenticated downloads, and immediate Vue parity.
- URL contract tests in both modules.
- An emulator smoke test for the native first-run flow.

## APK artifacts

The `Android checks and APK` workflow publishes separate `tracking-web-apk` and `tracking-native-apk` artifacts on every relevant branch or pull request. Tagged releases publish stable APK filenames on the Releases page.

Release signing uses these encrypted GitHub secrets:

- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

The Base64 value must contain the persistent production keystore. Back it up securely: losing it prevents users from installing future versions over the existing application.
