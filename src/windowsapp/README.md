# Windows WebView2 client

Tracking Windows Web is a lightweight WPF application for Windows 10 and newer. It renders the hosted Vue frontend through the Microsoft Edge WebView2 runtime, so frontend UI changes appear without rebuilding the Windows application.

## Install

- Normal users should download the signed `tracking-windows-web.msix` from GitHub Releases.
- The portable `tracking-windows-web.zip` can be extracted and launched with `Tracking.Windows.exe`.
- Install the Microsoft Edge WebView2 Evergreen Runtime if it is not already present.

On first launch, enter the full HTTP or HTTPS server address. The setting is stored under the current user's local application-data directory. WebView2 owns cookies and browser storage inside its application profile; secrets are not written to the server-address file.

## Develop and test

Use Visual Studio 2022 or the .NET 8 SDK on Windows:

```powershell
dotnet test Tracking.Windows.Tests/Tracking.Windows.Tests.csproj
dotnet run --project Tracking.Windows/Tracking.Windows.csproj
```

`Tracking.Core` contains the platform-neutral server-address contract and its tests. `Tracking.Windows` contains the WPF/WebView2 shell. `packaging` contains the MSIX manifest and visual assets. The GitHub workflow produces both a portable ZIP and an unsigned development MSIX for pull requests; tagged Releases require the configured signing certificate.

## Why there is no second native WinUI client

The WebView2 client already behaves as a conventional Windows application while following Vue changes automatically. A separate WinUI implementation would duplicate every screen and authentication workflow. The project can add one later if real usage identifies Windows-specific workflows that justify that maintenance cost.
