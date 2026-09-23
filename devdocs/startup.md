# Startup flow architecture

The startup implementation is intentionally small. It does not introduce a monitoring service or a second health subsystem.

## Flow

`main.ts` calls `waitForServer()` before `checkAuth()`.

`waitForServer()` calls the existing `/api/setup/status` endpoint. A successful response means the backend can serve application requests, so authentication can safely run.

Connection/network failures update `serverStartupPhase` and retry. Unexpected HTTP/application errors are not silently converted into startup retries.

## Adding another phase

Update `ServerStartupPhase` in `state/serverStartup.ts`, `phaseForAttempt()`, the message/detail mapping in `App.vue`, and this documentation.

Do not turn phases into a fake progress percentage. They describe expected container startup stages, not measured work.

## Testing guidance

Test `isBackendUnavailable()` with network-style errors and ordinary application errors. Test phase mapping independently from Vue rendering. A browser-level test should verify that the startup screen disappears once `/api/setup/status` responds.
