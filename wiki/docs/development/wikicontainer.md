# Wiki Container

The repository includes a small, isolated Wiki Container for serving the project documentation locally.

## Start

From the repository root:

    docker compose -f src/wikicontainer/compose.yaml up --build

The wiki is available at <http://localhost:999/> by default.

## Live reload

The Compose configuration bind-mounts the repository's `/wiki` directory into the container at `/wiki`.

MkDocs watches that mounted directory, so edits to:

- Markdown documentation;
- `mkdocs.yml`;
- navigation;
- images and other wiki assets

are picked up automatically without rebuilding the image.

## Bundled wiki

The Docker image also copies the repository's `/wiki` into the image during the build.

This means the image has a complete wiki snapshot and can be run independently of the repository. The development Compose file intentionally mounts the live checkout over that bundled copy so documentation changes can be previewed immediately.

## Scope

The Wiki Container only serves the wiki. It does not manage application containers, databases, application images, Docker projects, environments, or the Plugin Runtime.

The Plugin Runtime remains part of the application's normal Compose/deployment configuration.
