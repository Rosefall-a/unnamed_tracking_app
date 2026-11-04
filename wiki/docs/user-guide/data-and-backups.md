# Data, Exports and Backups

Unnamed Tracking App stores library records in PostgreSQL and larger user files on the application's persistent data directory.

## Automatic backups

The application backs up the whole PostgreSQL database: every account, library, note, achievement, setting and link. By default it does this once a day and keeps the newest **7** backups. An admin can change both, turn backups off, run one now, download one or delete one under **Settings > Administration > Backups**.

```text
/data/backups/database/
```

Each backup is checked after it is written, before any older one is removed. If a backup fails, nothing is removed, the reason shows on that page, and automatic backups try again an hour later. To restore one, stop the application and run:

```bash
docker exec -i <db container> pg_restore --clean --if-exists -U <user> -d <database> < database-<time>.dump
```

Covers, screenshots, clips and saves are not inside these backups, and the backups are stored on the same disk as the application. Copy `/data` somewhere else as well to protect against losing that disk.

## Library export

The library export is a user-scoped JSON snapshot containing games, movies, TV shows and anime:

```http
GET /api/export/library
```

## Library import

The generic importer is currently more limited than export. It accepts game records and recreates them for the authenticated user.

It does **not** generically restore:

- movies
- TV shows
- anime
- screenshots or other folder assets
- save archives

Game folder-name collisions are given a new available folder name rather than overwriting an existing game.

## Save files and game assets

Game assets and save archives are stored on disk under the owning user's directory. They are not part of the JSON library export.

A game's persistent directory is:

```text
/data/users/<user-id>/games/<folder-location>/
```

Game assets use files such as `key_art.png`, `banner.png`, `logo.png`, and `icon.png`. Notes, screenshots and clips have their own directories. Clip thumbnails are kept beside the clips.

Notes are plain `.md` files. Their extra details (created date, pin, tags, the achievement they are tied to) and their saved versions are stored in PostgreSQL, so a note's history is part of the database, not the folder.


### Game note titles

Game notes use a human-readable title rather than requiring a filesystem-style name. Titles may contain spaces and common punctuation, for example "what is this for", "Quest Log - Main Story", or "Build #2 (final!)".

Titles must not contain path separators, control characters, drive-style paths, or other path-like values. Empty titles, ".", "..", hidden/path-like names, and Windows-reserved device names are rejected. A trailing ".md" is treated as the note's display title without the extension for compatibility.

Creating a note whose title already exists does **not** replace the existing note. The API returns a conflict and the Notes editor keeps the operation in an editable state so the user can choose another title or cancel.

Editing an existing note saves its current title normally. Renaming uses a dedicated rename operation: the destination must be unused, the existing content is preserved, and renaming to the same title is a no-op. A failed rename leaves the original note in place.

The Notes UI translates validation, conflict, loading, saving, deletion, and rename failures into user-facing messages rather than displaying raw backend status or JSON responses.

Named save archives are stored under the game directory in `saves/` or `world_saves/`.

## The image cache

Smaller copies of artwork are kept in a cache folder for each user:

```text
/data/users/<user-id>/.cache/
```

`asset-previews/` holds resized copies of a game's banner and cover, and `media-images/` holds local copies of movie, TV and anime posters and backdrops. Everything in it can be rebuilt from the originals (or downloaded again), so it does not need to be backed up, and deleting it is safe. It is rebuilt as pictures are needed.

## Moving a deployment

A complete deployment therefore needs both:

1. PostgreSQL data; and
2. the persistent application data directory.

A JSON library export does not reproduce all stored files, and copying only `/data` does not reproduce the PostgreSQL database.
