# Android app

The Android client is a native Jetpack Compose application. It communicates with
the existing FastAPI backend through OkHttp and renders Android-native Material 3
screens; it does not use WebView.

## User setup

1. Install the debug or release APK on Android 10 or newer.
2. Open the app and enter the full URL of the running tracking-app frontend.
3. Sign in normally. The server's `HttpOnly` session cookie is retained by the
   app's private persistent cookie store and sent only to matching server URLs.

Use HTTPS whenever the server is reachable outside a trusted LAN. Cleartext HTTP
is enabled only to support local self-hosted addresses. The app does not bypass
certificate failures.

Always include `http://` or `https://` when the server's protocol is known. When
omitted, private LAN and emulator addresses default to HTTP while public hostnames
default to HTTPS. TLS certificate verification is never bypassed.

## Development

Open `src/androidapp` in Android Studio, allow Gradle sync to finish, and run the
`app` configuration. The default server is blank so the first-launch setup is
shown. To bake a default into a local build:

```properties
# ~/.gradle/gradle.properties (do not commit real deployment URLs)
trackingAppServerUrl=https://tracker.example.com
```

Command-line checks, from this directory with Gradle 8.9 installed:

```bash
gradle testDebugUnitTest lintDebug assembleDebug
gradle connectedDebugAndroidTest  # with an emulator/device attached
```

The application is split into a small native architecture:

- `MainActivity.kt` hosts the edge-to-edge Compose UI without an Android title bar.
- `TrackingApp.kt` owns native setup, login, navigation, library and data screens.
- `network/ApiClient.kt` owns HTTP/HTTPS requests and actionable TLS errors.
- `network/PersistentCookieJar.kt` persists first-party session cookies privately.
- `ServerUrl.kt` validates protocol and server-address behaviour.
- `MainActivityTest.kt` verifies the native first-run configuration flow.

## APK artifacts

The `Android checks and APK` GitHub Actions workflow runs unit tests, lint, an
emulator smoke test, and `assembleDebug`. Its `android-debug-apk` artifact can be
downloaded from the completed workflow run. Debug APKs are not Play Store release
artifacts; production signing keys must be kept in GitHub encrypted secrets and
configured in a separate release process.
