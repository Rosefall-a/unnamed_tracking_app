using Tracking.Core;
using Xunit;

namespace Tracking.Windows.Tests;

public class ServerAddressTests
{
    [Theory]
    [InlineData("tracker.example.com", "https://tracker.example.com/")]
    [InlineData("192.168.1.20:5173", "http://192.168.1.20:5173/")]
    [InlineData("http://tracker.lan:8080/", "http://tracker.lan:8080/")]
    public void NormalizesSupportedServerAddresses(string input, string expected) =>
        Assert.Equal(expected, ServerAddress.Normalize(input).AbsoluteUri);

    [Theory]
    [InlineData("")]
    [InlineData("file:///tmp/archive")]
    [InlineData("https://user:secret@example.com")]
    [InlineData("https://example.com/?token=secret")]
    public void RejectsUnsafeServerAddresses(string input) =>
        Assert.Throws<ArgumentException>(() => ServerAddress.Normalize(input));
}
