# Movie, TV and Anime Libraries

These three libraries share one layout, so what is described here applies to
all of them. Their own pages cover what is specific to each.

## Rank

A title with a score gets a **rank**: its place among every title you have
scored in that library, highest score first. Titles with equal scores are
ordered by name, so each rank is different. Ranks are worked out over the whole
library, so they stay the same whether you are searching, scrolling or looking
at only one page of it.

Rank shows as a badge on cards, in the Rank column of the list layout, and as
the **Sort: Rank** order. Movies, TV shows and anime are ranked separately.

## Filtering from a title's page

The genres on a title's page are links. Clicking one opens that library with
only that genre selected and the filter panel open, replacing whatever filters
were left on before. This works on Movie, TV and Anime pages.

## Pictures

Posters and backdrops are stored by TMDB or AniList, but your server keeps its
own small copy of each one. The first time a picture is needed, the server
downloads it, shrinks it (posters to 400 pixels wide, backdrops to 1920) and
stores it. After that, pages load it from your own server and nothing waits on
another site.

- Changing a title's poster or backdrop address makes a fresh copy.
- If a download fails, your browser is sent to the original address instead, so
  a picture never just disappears.
- The server only fetches public web addresses. Addresses that point at your own
  machine or local network are refused.
- The copies are a cache and can be deleted at any time. They are made again when
  needed. See [Data, Exports and Backups](data-and-backups.md).

Libraries also load pictures lazily: only the cards near the screen fetch
theirs, and more load as you scroll.

## Editing

Movies, TV shows and anime use the same Add and Edit dialog layout. The search
box at the top fills in the form from a metadata provider, and fields you have
changed yourself are kept rather than overwritten (the dialog tells you which
it skipped).
