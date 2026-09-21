# Database migrations

Updating the app is: pull the new version, start it. The backend container runs
`python -m src.database.migrate` before the server starts, which brings the
database up to date on its own.

## What happens on start

| Database state | What the runner does |
| --- | --- |
| Empty | Builds everything from the migrations |
| Version is in this code's history | Runs the migrations newer than it |
| Version is not in the history, or tables exist with no version | Attaches the database to the starting migration (data untouched) and runs every migration after it. Then checks the models' tables and columns exist. If something is still missing (no migration creates it) it stops, names it, and forgets the attachment so the next start checks again |

Two containers starting together are safe (a database lock serialises them).
A real failure stops the container with the reason, instead of retrying.

## Writing a migration

- `alembic revision -m "what changed"` inside the backend container, then edit it.
- Keep one line of history: the runner refuses to start with two heads.
  If two branches both add a migration, rebase one onto the other's revision.
- Make it safe to run twice: `IF NOT EXISTS` for indexes and columns, check
  before adding a constraint, dedupe data before adding a unique constraint.
  See `c9a2e6b4d8f1_restore_constraints_tv_season_check.py`.
- Write a `downgrade()` that undoes it.
- Never edit a migration that has already shipped. Add a new one.

## Squashing the history

It is safe to replace the history with a new baseline: every existing install
is adopted onto it automatically on its next start (see the table above), as
long as the baseline creates the same schema the old chain ended with.
Check that with a fresh `alembic upgrade head` on an empty database and a
schema comparison against a database from the old chain before merging.
