# Android app

The Android client is a deliberately thin WebView shell around the existing Vue
application. The server remains the single source of truth, so every current and
future web feature is available without maintaining a second UI or API client.

## User setup

1. Install the debug or release APK on Android 10 or newer.
2. Open the app and enter the full URL of the running tracking-app frontend.
3. Sign in normally. The `HttpOnly` session cookie is retained by Android's
   WebView cookie store and is sent only to the server that issued it.

Use HTTPS whenever the server is reachable outside a trusted LAN. Cleartext HTTP
is enabled only to support local self-hosted addresses. The app does not bypass
certificate failures.

Uploads use Android's system file picker. Authenticated downloads are handed to
Download Manager with the current session cookie. Back navigates WebView history;
the action-bar menu can reload, change servers, or open the current page in the
default browser.

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

The application code is intentionally small:

- `MainActivity.kt` owns WebView lifecycle, cookies, file selection, downloads,
  navigation, and server switching.
- `ServerUrl.kt` validates the configured server URL and has JVM unit tests.
- `MainActivityTest.kt` verifies the first-run configuration flow on Android.

## APK artifacts

The `Android checks and APK` GitHub Actions workflow runs unit tests, lint, an
emulator smoke test, and `assembleDebug`. Its `android-debug-apk` artifact can be
downloaded from the completed workflow run. Debug APKs are not Play Store release
artifacts; production signing keys must be kept in GitHub encrypted secrets and
configured in a separate release process.
