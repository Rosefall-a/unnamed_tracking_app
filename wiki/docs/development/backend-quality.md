# Backend quality checks

The rework of [PR250](https://github.com/Rosefall-a/unnamed_tracking_app/pull/250) includes [PR432](https://github.com/Rosefall-a/unnamed_tracking_app/pull/432), which was retargeted and merged into the maintenance branch first. Continued cleanup is published on the [ObsoleteLabs fork branch](https://github.com/obsoletelabs/unnamed_tracking_app_2/tree/fix/pylint-ci-rework).

## CI behavior

Backend tests, plugin runtime tests, migration graph validation, module size, mypy, and Pylint run independently. The reusable Pylint workflow runs once. The final `backend-checks` summary fails when any required job fails or is skipped, preserving the required status name while allowing every diagnostic check to run.

Ruff format, lint, and autofix run independently. Autofix is the only writer, targets the actual same-repository PR head, and checks for a stale head before pushing. A formatting failure does not prevent autofix. Commands piped through `tee` propagate failures, and diagnostic artifacts upload after failures.

Pylint uses the shared configuration and `--fail-under=10`. Its score is not parsed from rounded console output. The physical 1,000-line source limit is checked independently and cannot be bypassed by a Pylint directive.

## Agreed Pylint policy

- Missing module, class, and function docstrings are relaxed globally. Public contracts, security boundaries, and non-obvious business logic still need useful documentation.
- SQLAlchemy and Pydantic data models do not need artificial public methods.
- Ruff retains a 100-character formatting target; Pylint checks a 120-character maximum.
- Correctness checks, including `import-error`, `no-member`, `not-callable`, undefined names, and unused imports, remain enabled globally.
- Existing workflows and declared interfaces may have local complexity exemptions for argument counts, locals, branches, statements, or boolean expressions. These preserve explicit validation and transaction steps without raising global limits.
- Similar route bodies, response shapes, field declarations, and compatibility adapters may have local `duplicate-code` exemptions. Similarity alone does not justify changing an application boundary.

Old blanket file-header disables have been removed. Exceptions use the relevant statement, class, or an explicit disable/enable pair around the affected workflow. A 10/10 score means the code passes this documented policy; it does not mean every complexity or similarity finding has been eliminated.

Broad exception handling remains limited to boundaries with defined recovery behavior, such as external-provider fallbacks, per-entry import failure reporting, plugin isolation, and background retry loops. Inner logic should catch the specific failures it can handle.

## Cleanup and architectural boundaries

The cleanup fixes source issues rather than hiding them behind file-wide rules: fixture registration, shadowed upload arguments, invalid merge-time names, timestamp handling, provider normalization, public permission lookups, session/job lifecycle handling, and typed SQLAlchemy expressions. Compatibility exports use explicit `__all__` declarations.

The games router composes its existing responsibilities from `game_assets`, `game_files`, `game_profiles`, `game_checklists`, and `game_metadata`. Basic and advanced notes share the existing `game_notes` module. Shared route ownership, paths, validation, and history helpers live under `api/routes/utils/games.py`. Route order, authentication dependencies, public parameters, and OpenAPI component identities are preserved. Shared title normalization and Steam CDN URLs reside in the existing title/provider modules.

Plugin infrastructure remains in the host application. Plugin implementations are not copied into the host to satisfy tests. Runtime acquisition, trust, permissions, updates, and gateway access retain the supported public contract and their security boundaries.

The migration repair preserves the existing session-network revision identity and predecessor columns on downgrade. Revision `65acf36995e5` joins the maintenance/main histories; it does not introduce an unrelated schema feature.

## Verification

From `src/backend`, run:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy --config-file pyproject.toml src
python -m pylint --rcfile=pyproject.toml --fail-under=10 src
```

The database-backed backend suite runs against PostgreSQL in CI. With the development stack running:

```bash
docker compose exec -e PYTHONPATH=/app backend python -m pytest tests -q
```

Focused checks cover session persistence and OIDC state/account linking, deployment environment locks and encrypted secrets, media lifecycle and exact statistics, imports/exports, provider fallbacks, plugin authorization, package integrity, and runtime cleanup. Before/after comparisons validate the complete OpenAPI document and selected policy/calculation outputs. PostgreSQL migration replay and production container smoke checks remain part of CI; supplementary SQLite checks do not replace them.

Breaking changes: no public API changes. Individual backend checks have separate result names, and the required `backend-checks` summary covers every backend job, including Pylint.
