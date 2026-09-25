# Data, Exports and Backups

Unnamed Tracking App stores library records in PostgreSQL and larger user files on the application's persistent data directory.

## Automatic backups

The application runs an in-process automatic backup loop. It runs once at startup and then every 24 hours.

Automatic backups are per-user JSON snapshots containing games, movies, TV shows and anime.

Up to **7** automatic backups are retained for each user:

\`\`\`text
/data/backups/<user-id>/
\`\`\`

These are a rolling safety net, not a complete deployment backup.

## Library export

The library export is a user-scoped JSON snapshot containing games, movies, TV shows and anime:

\`\`\`http
GET /api/export/library
\`\`\`

## Library import

The generic importer is currently more limited than export. It accepts game records and recreates them for the authenticated user.

It does **not** generically restore:

- movies
- TV shows
- anime
- screenshots or other folder assets
- save archives
- bounties

Game folder-name collisions are given a new available folder name rather than overwriting an existing game.

## Save files and game assets

Game assets and save archives are stored on disk under the owning user's directory. They are not part of the JSON library export.

A game's persistent directory is:

\`\`\`text
/data/users/<user-id>/games/<folder-location>/
\`\`\`

Game assets use files such as \`key_art.png\`, \`banner.png\`, \`logo.png\`, and \`icon.png\`. Notes, screenshots and clips have their own directories.

Named save archives are stored under the game directory in \`saves/\` or \`world_saves/\`.

## Moving a deployment

A complete deployment therefore needs both:

1. PostgreSQL data; and
2. the persistent application data directory.

A JSON library export does not reproduce all stored files, and copying only \`/data\` does not reproduce the PostgreSQL database.
