# Movies

Movies are user-scoped records with metadata, status, rating, dates, artwork, lists, activity, and optional rewatch history.

Create a movie manually or select a result from the configured movie metadata provider. The library supports search, filters, sorting, list membership, and bulk workflows shared with other media libraries. The detail page exposes editing, activity, related titles, and recommendations when provider data is available.

Deleting a movie moves it to trash. Restore returns it to the library; purge permanently removes it. Metadata refresh respects supported locked-field behavior and requires the relevant provider credentials to be configured by an administrator.

## Where you left off

A movie you haven't finished shows **Left off at** under its status. Type
the time you stopped at, as minutes (`74`) or hours and minutes (`1:14`),
and press Enter or click away to save it. With a known runtime, a bar shows
how far through you are. Leave it blank to clear it.

- Saving a position on a Plan to Watch movie moves it to Watching.
- On Hold keeps its status: it's a paused watch.
- Marking the movie Completed clears the position.

The same value can be set in the movie's **Edit** form.

## Editing

The **Edit** form only changes what it shows. A movie's note, rewatch count,
priority, dates, countries, languages and other ratings are kept as they are
when you save it. The same applies to TV shows and anime.
