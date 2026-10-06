# Backend quality rework checkpoint

PR [250](https://github.com/Rosefall-a/unnamed_tracking_app/pull/250) is being repaired on its existing branch. PR [432](https://github.com/Rosefall-a/unnamed_tracking_app/pull/432) was retargeted and merged into that branch first. PR250 is not ready to merge until the remaining quality work is complete.

## Repaired failures

- Restore the SQLAlchemy enum import used by movie and TV status columns.
- Use one consistent airing-job running flag; cover status, duplicate starts, and cleanup after success/failure.
- Reconcile the maintenance branch's session-network migration with main. The predecessor already owns the same columns, so the repair uses the existing guarded migration helper and preserves predecessor columns on downgrade. Keep the existing revision identity for databases that applied it, and join the two heads with revision `65acf36995e5`. This is a migration repair, not a new schema feature.
- Normalize branding images in place before conversion so mypy can verify the image type; retain EXIF orientation and metadata removal.
- Apply Ruff's safe import/format fixes. The remaining lint findings are reported separately.

## CI behavior

Backend tests, plugin runtime tests, migration graph validation, module size, mypy, and pylint run independently. The dedicated pylint workflow is reusable and is called once by the backend workflow. A final `backend-checks` summary waits for all backend jobs and fails if any fails or is skipped, preserving the existing required status name without making the checks depend on each other's success. Ruff format, lint, and autofix also run independently; the autofix job is the only writer and targets the actual same-repository PR head. Commands piped through `tee` use Bash's failure propagation, and diagnostic artifacts upload after failures.

The duplicate 9/10 pylint check in the backend test job is replaced by the existing dedicated 10/10 job. That job reads the shared configuration and uses pylint's numeric `--fail-under=10` gate rather than parsing a rounded score. Its workflow-only `duplicate-code` disable has been removed.

The 1,000-line size gate now counts physical lines correctly and cannot be bypassed by `pylint: disable=too-many-lines`. The following modules still require coherent extraction:

| Module | Lines at this checkpoint |
| --- | ---: |
| `src/api/routes/games.py` | 2,723 |
| `src/api/routes/library_sync.py` | 1,010 |
| `src/features/metadata/anime/anilist.py` | 1,011 |

## Pylint policy and audit

The agreed policy relaxes missing module/class/function docstrings and the minimum public-method count for SQLAlchemy/Pydantic models. Public contracts, security boundaries, and non-obvious business logic should still have useful documentation. The line-length setting is restored from 180 to the repository's documented 120 characters.

The initial source inventory found **131 suppression directives across 125 files**, including **99 file headers**. Common suppressed rules included missing function docstrings (66 directives), module docstrings (54), class docstrings (42), duplicate code (33), minimum public methods (30), local-variable count (25), and broad exception handling (22).

An audit of a temporary source copy with all inline pylint directives removed exposes **999 findings**, with a **9.43/10** score under the agreed policy. The largest groups are redundant import aliases (218), protected access (150), duplicate code (143), unused imports (78), too many locals (64), and broad catches (60). That audit does not modify application files. It prevents the existing suppressed score from being mistaken for the actual cleanup scope.

## Recommended cleanup order

1. Fix the remaining Ruff lint findings. Most are reused pytest fixtures imported under the same name as fixture parameters. Register or extract those fixtures deliberately rather than ignoring all fixture-related errors. The other findings concern an unused variable, a shadowed import, a lambda assignment, and an unspecified `zip` length contract.
2. Remove redundant `X as X` import aliases. Preserve intentional compatibility exports with an explicit `__all__` and verify callers before changing facade modules.
3. Remove blanket file-header pylint disables feature by feature. Delete redundant docstring/data-model disables under the shared policy, then address genuine unused code, mutable-state naming, unsafe closures, and dependency cycles with regression coverage.
4. Split large routes along existing API/feature boundaries. Share only actual duplicated responsibilities; similar response models or migration declarations are not automatically reasons for a new generic abstraction.
5. Review broad exception handlers individually. Runtime/plugin isolation and startup boundaries may need a broad catch with logging and defined failure behavior. Inner business logic should catch the actual failures it can handle.
6. Verify SQLAlchemy, Alembic, and Pydantic inference findings against real behavior. Keep correctness rules such as `no-member` and `not-callable` enabled globally. If a demonstrated framework limitation remains, use a narrowly scoped, explained exception rather than disabling a rule throughout a file.
7. Reassess the inherited global `import-error` disable with all backend dependencies installed. It should not hide broken imports as the cleanup progresses.

Additional policy candidates should be reviewed separately: aligning the positional-argument limit with the existing total-argument limit, accepting documented lazy imports for initialization cycles/optional dependencies, and keeping third-party protected API use explicitly justified. Complexity limits should not be raised simply to obtain a score.

## Verification limits

The focused regression suite covers model status columns, airing jobs, branding, migration metadata, and guarded session-network migration behavior. Mypy checks the backend source. Workflow verification executes the actual migration/size scripts, parses changed shell commands, and exercises detached-head autofix pushes plus stale-head protection against a local bare repository. The issue forms are parsed and checked for unique field IDs.

The session-network regression uses a real SQLite database to verify column/data preservation, while PostgreSQL migration replay and the full backend suite remain required in CI. Production runtime smoke remains required too. Local Windows execution cannot substitute for the Linux database/container workflows.

Breaking changes: no public API changes. Strict size enforcement changes, and individual backend results now have separate names. The required `backend-checks` status is preserved and covers every backend job, including pylint.
