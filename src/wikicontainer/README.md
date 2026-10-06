# Wiki Container

The Wiki Container is a small, self-contained MkDocs container for the repository wiki.

## Start

From the repository root:

    docker compose -f src/wikicontainer/compose.yaml up --build

Then open http://localhost:999/.

The default port can be changed with `WIKI_CONTAINER_PORT` and `WIKI_CONTAINER_BIND_PORT`.

## Development reload

Compose bind-mounts the repository's `/wiki` directory into the container at `/wiki`. MkDocs watches that directory, so changes to Markdown, `mkdocs.yml`, navigation, or other wiki content are picked up automatically without rebuilding the image.

The image itself also contains a copy of `/wiki` from the checkout used when it was built. This means the image remains self-contained when run without the development bind mount.

## What this container does not do

This is intentionally only a wiki container. It does not manage the application, Docker Compose projects, application images, environments, databases, or the Plugin Runtime.

The application's Plugin Runtime remains owned by the normal application Compose/deployment configuration.
