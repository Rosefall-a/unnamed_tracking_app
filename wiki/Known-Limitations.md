# Known Limitations and Documentation Findings

This page records concrete gaps found during the initial wiki audit. It is not a claim that every item is a bug.

## Configuration/schema gaps

### 1. Multiple .env examples are not authoritative

The repository has a root `example.env` and a production `src/docker-container/.env.example`, plus Compose interpolation variables.

They describe different deployment modes and do not enumerate exactly the same values.

**Follow-up:** create a typed, testable configuration inventory and decide which values are environment configuration versus database Settings.

### 2. Duplicate SECRET_KEY entry

The root `example.env` currently defines `SECRET_KEY` twice.

**Follow-up:** remove the ambiguity and ensure the generated example contains one authoritative value.

### 3. VITE_API_BASE_URL appears unused

It is present in `example.env` and `vite-env.d.ts`, but current frontend service code uses relative API URLs and the Vite proxy.

**Follow-up:** either make it a real API-base configuration or remove it.

### 4. Environment and database settings have intentionally diverged

Provider/OIDC configuration has moved toward database-backed administrator settings while environment fallbacks remain.

This is useful for compatibility but makes the configuration model harder to explain.

## Documentation drift

### 5. OIDC documentation says verified email is required

The current callback requires an email claim but no longer rejects an explicitly false `email_verified` claim. The old check is commented out.

`docs/OIDC.md` and `docs/SETUP.md` still describe verified email as mandatory.

**Follow-up:** update those documents to match the current callback.

### 6. Production-container docs overstate runtime smoke testing

The production docs describe the image build and startup architecture, but the current CI workflow does not run the full PostgreSQL/startup/frontend smoke sequence.

Issue #206 explicitly tracks this missing validation.

### 7. Migration documentation has drifted from the current entrypoint

`docs/migrations.md` describes `python -m src.database.migrate`, while the current backend/production entrypoints invoke Alembic directly.

The migration runner implementation still exists, so this needs an intentional decision rather than a blind documentation edit.

## Open issues directly relevant to documentation/operations

- **#197** — comprehensive GitHub wiki.
- **#205** — production hardening/observability.
- **#206** — optional production runtime smoke tests.
- **#204** — HTTPS/TLS.
- **#184** — Playnite duplicate-create/sync robustness.
- **#185** — Playnite library sync should not make the frontend appear unavailable.
- **#144** — settings UX/interaction audit.
- **#129 / #124** — authentication/integration secret-disclosure audits.
- **#143** — authentication-flow regression coverage.

## Closed/not-planned issue audit

The initial pass found many completed/merged issues and PRs, but the GitHub connector's issue search does not expose a reliable filter for `state_reason=not_planned`. Therefore this initial wiki does **not** claim a complete list of closed-as-not-planned issues.

Where an old issue is relevant to configuration or documentation, it should be rechecked directly before being described as resolved or not planned.

## What this wiki intentionally does not promise

- TLS is not currently built into the production image.
- Direct public-internet exposure is not a hardened deployment mode.
- Production image CI is not equivalent to a full runtime integration test.
- Environment variables do not represent every setting available through the web UI.
- The Playnite extension's full implementation documentation belongs in its own repository.
