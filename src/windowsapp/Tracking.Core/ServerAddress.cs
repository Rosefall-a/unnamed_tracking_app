using System.Net;

namespace Tracking.Core;

public static class ServerAddress
{
    public static Uri Normalize(string rawValue)
    {
        var value = rawValue.Trim();
        if (value.Length == 0) throw new ArgumentException("Enter your tracking server address.");
        if (!value.Contains("://", StringComparison.Ordinal))
            value = $"{DefaultScheme(value)}://{value}";
        if (!Uri.TryCreate(value.TrimEnd('/'), UriKind.Absolute, out var uri) ||
            (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps) ||
            string.IsNullOrWhiteSpace(uri.Host) || !string.IsNullOrEmpty(uri.UserInfo) ||
            !string.IsNullOrEmpty(uri.Query) || !string.IsNullOrEmpty(uri.Fragment))
            throw new ArgumentException("Enter a valid http:// or https:// server address without credentials, a query, or a fragment.");
        return uri;
    }

    private static string DefaultScheme(string authority)
    {
        var host = authority.Split('/')[0].Split(':')[0].ToLowerInvariant();
        if (host is "localhost" or "127.0.0.1" or "10.0.2.2") return Uri.UriSchemeHttp;
        if (IPAddress.TryParse(host, out var address))
        {
            var bytes = address.GetAddressBytes();
            if (bytes.Length == 4 &&
                (bytes[0] == 10 ||
                 (bytes[0] == 192 && bytes[1] == 168) ||
                 (bytes[0] == 172 && bytes[1] is >= 16 and <= 31)))
                return Uri.UriSchemeHttp;
        }
        return Uri.UriSchemeHttps;
    }
}
