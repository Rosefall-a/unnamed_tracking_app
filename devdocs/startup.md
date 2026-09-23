# Startup flow architecture

main.ts waits for waitForServer before checkAuth.

waitForServer uses the existing setup-status endpoint as the readiness boundary. Network failures update the startup phase and retry with backoff. Ordinary application errors are not silently converted into startup retries.

The startup UI describes expected container stages rather than pretending to know migration progress.

## Testing

Test network-style backend failures, ordinary HTTP/application errors, phase mapping, and browser rendering. A browser-level test should verify the startup screen disappears once setup-status responds successfully.
