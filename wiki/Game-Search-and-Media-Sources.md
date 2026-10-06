# Game search and media sources

The add-game flow keeps game discovery and artwork discovery separate so the normal game search stays responsive.

## Game search

The game search field searches metadata providers as the user types, with a short debounce to avoid sending a request for every keystroke. Image-provider enrichment is disabled for this search path because artwork is not needed to identify a game.

SteamGridDB is an artwork source rather than a game metadata result source, so SteamGridDB-only results are not shown as games in the main search list.

## Media search

The Media step has a dedicated **Search artwork** action. It searches with image-provider enrichment enabled and combines portrait/key-art and banner candidates returned by the configured media providers, including SteamGridDB when configured.

This keeps artwork discovery available without slowing down the normal game search.
