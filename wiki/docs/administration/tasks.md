# Scheduled tasks

The backend job loop wakes every minute. Administrators configure jobs through Settings and can enable/disable them, choose an interval within each job's bounds, and request a manual run.

Current deployment-wide jobs are:

- **Plugin updates** — enabled by default, normally daily; follows each installed plugin's update policy and version pin.
- **Airing episode check** — enabled by default, normally every 30 minutes; checks TV/anime airing data and can be manually forced.
- **Media refresh** — disabled by default, normally daily; fills missing episode metadata and corrects stale media data.

Per-user scheduled AniList imports are also processed in bounded batches when enabled in user preferences. External notification deliveries use the same loop, but their retry schedule is owned by the notification delivery coordinator rather than the task settings page.

The task view shows running state, last run, and a bounded summary. A failed iteration is logged and retried by a later loop; it does not stop the API server.

## Plugin schedules

Plugin API v1.1 packages can declare optional `scheduled_tasks` with an explicit
`tasks.background` permission. Each task appears with its plugin name, interval
bounds and Run now control. Scheduling starts off; an administrator enables it.
The existing job table stores intervals and results under an installation-bound
ID, so an update or ordinary reinstall retains the schedule and a new installation
does not inherit another installation's settings.

Tasks use the plugin's existing background administrator identity, rather than
the person currently pressing Run now. Both background and action permissions
are checked before dispatch and again by the isolated runtime. A stopped,
disabled or incompatible plugin, revoked grant, inactive background administrator
or runtime outage pauses controls with an explanation. Per-user subscriptions
remain independently required for delegated background operations.

A task must reference an existing action with a handler and no confirmation.
It receives only `_scheduled_task: {id, trigger}` with `manual` or `scheduled`;
there is no arbitrary action/user override. Existing process limits and the
30-second action wall limit apply. Runs of the same task do not overlap. Public
results retain only `completed` and a summary of at most 512 characters. Removing
a declaration hides its job without deleting saved settings.

Invalid intervals stay in the edited field with nearby guidance. Saving one job
or refreshing run status preserves other drafts. Settings confirms successful
writes for twelve seconds, then shows a quiet Saved state; a concurrent failed
write cannot be hidden by another successful response. Native and sandboxed
scrollbars use the active semantic palette.
