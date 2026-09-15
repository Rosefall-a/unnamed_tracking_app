using System.IO;
using System.Windows;
using Microsoft.Web.WebView2.Core;
using Tracking.Core;

namespace Tracking.Windows;

public partial class MainWindow : Window
{
    private static readonly string SettingsDirectory = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "ArchiveTracking");
    private static readonly string ServerFile = Path.Combine(SettingsDirectory, "server.txt");
    private Uri? serverUri;

    public MainWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (!File.Exists(ServerFile)) return;
        ServerInput.Text = await File.ReadAllTextAsync(ServerFile);
        await ConnectAsync();
    }

    private async void Connect_Click(object sender, RoutedEventArgs e) => await ConnectAsync();

    private async Task ConnectAsync()
    {
        try
        {
            serverUri = ServerAddress.Normalize(ServerInput.Text);
            ErrorText.Text = "";
            Directory.CreateDirectory(SettingsDirectory);
            await File.WriteAllTextAsync(ServerFile, serverUri.AbsoluteUri.TrimEnd('/'));
            await Browser.EnsureCoreWebView2Async();
            Browser.CoreWebView2.Settings.AreDevToolsEnabled = false;
            Browser.CoreWebView2.Settings.IsPasswordAutosaveEnabled = true;
            Browser.CoreWebView2.NavigationCompleted -= NavigationCompleted;
            Browser.CoreWebView2.NavigationCompleted += NavigationCompleted;
            Browser.Visibility = Visibility.Visible;
            SetupPanel.Visibility = Visibility.Collapsed;
            Browser.Source = serverUri;
        }
        catch (Exception exception)
        {
            Browser.Visibility = Visibility.Collapsed;
            SetupPanel.Visibility = Visibility.Visible;
            ErrorText.Text = exception is ArgumentException
                ? exception.Message
                : "The WebView2 runtime could not start. Install Microsoft Edge WebView2 and try again.";
        }
    }

    private void NavigationCompleted(object? sender, CoreWebView2NavigationCompletedEventArgs e)
    {
        if (e.IsSuccess) return;
        Browser.Visibility = Visibility.Collapsed;
        SetupPanel.Visibility = Visibility.Visible;
        ErrorText.Text = e.WebErrorStatus == CoreWebView2WebErrorStatus.CertificateIsInvalid
            ? "HTTPS certificate validation failed. Fix the certificate, or use http:// only for a trusted local server."
            : $"The server could not be reached ({e.WebErrorStatus}). Check the address and try again.";
    }
}
