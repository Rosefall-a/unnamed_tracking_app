# Data Importers

Data importers bring library and tracking data from another application into Unnamed Tracking App. Importers are one-way migration tools: the source application remains unchanged and Unnamed Tracking App creates or updates records in the current user's library.

## YamTrack CSV

Unnamed Tracking App supports YamTrack's native CSV export format. A YamTrack database connection, API plugin, or direct access to the YamTrack instance is **not required**.

### Export from YamTrack

1. Export your library from YamTrack as CSV.
2. Keep the exported CSV unchanged; do not open/save it in a spreadsheet if that changes the encoding or columns.
3. In Unnamed Tracking App, open **Settings → Export / Import**.
4. Choose **YamTrack CSV** and select the exported file.
5. Review the preview of new and existing titles.
6. Import the file and choose whether existing records should keep their current tracking data or accept the YamTrack values.

### What is imported

The importer uses the YamTrack title rows for:

- Movies
- TV shows
- Title
- Status
- Score/rating
- Start/end dates when present
- Tracking progress

For TV shows, YamTrack can export separate `tv`, `season`, and `episode` records. Season and episode rows are treated as tracking information for the parent TV show rather than imported as standalone titles. Watched episode numbers are preserved when they are present in the export.

Unsupported YamTrack media types are skipped and the import result reports how many records were not imported.

### Existing titles

Before changing existing library records, the importer provides a preview. Titles that already exist are not silently overwritten.

You can:

- Keep the existing record.
- Accept the YamTrack tracking data for a selected title.
- Apply the YamTrack values to all matching titles.

New titles are added normally.

### Metadata enrichment

The YamTrack CSV is a tracking export, so it may not contain all of the metadata displayed by Unnamed Tracking App. If configured, the importer can use the application's TMDB or OMDb integration to fill missing movie/TV details after import.

Metadata enrichment is optional. The migration still works without a TMDB or OMDb key.

### Limits and safety

- YamTrack CSV files are limited to **30 MB** per import.
- The CSV must be UTF-8 (a UTF-8 BOM is accepted).
- The importer validates the expected YamTrack columns before processing the file.
- Invalid or unsupported rows are skipped rather than creating incomplete standalone records.
- The importer does not modify the YamTrack instance.

## Importer design

Importers should prefer stable, user-exported formats over direct database access. This keeps migrations independent of the source application's database engine and internal schema versions.

When adding another importer, document:

1. How the user obtains the source export.
2. Which media types and tracking fields are supported.
3. How duplicate/existing records are handled.
4. What data cannot be migrated.
5. Any optional metadata/API credentials.
6. File-size, encoding, or format limitations.
