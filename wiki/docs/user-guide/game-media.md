# Game Media and Files

A game's page keeps your screenshots, clips, soundtrack, saves, docs and
Minecraft worlds. They all work the same way: one grid of cards, one add card,
and the same tools above it. Only what is specific to the kind of file
differs.

| Tab | What it holds |
| --- | --- |
| Screenshots | Images, shown full size in a viewer. |
| Clips | Videos, with a saved preview picture and the real length on each card. |
| Soundtrack | Audio. A track plays right on its card. |
| Saves | Named save files, each with a history of versions. |
| Docs | Manuals, guides and any other file. |
| World Map | Minecraft worlds, shown on Minecraft games. Zip the world folder (the one with `level.dat`) and add it. |

## Adding files

There are three ways, and they all do the same thing:

- Click the big **add card** at the start of the grid.
- Drop files anywhere on the page. A drop box appears over the grid, not in the
  middle of the screen.
- Paste an image with Ctrl+V (screenshots).

Several files can be added at once. Saves and worlds ask you to name them
first, since one game can hold any number of named saves.

## Finding things

- **Search** matches the title, the file name, your note, the tags and the
  name of the achievement a file is tied to.
- **Sort** by Newest first, Oldest first or Name.
- **Filter** to everything, or only the files tied to an achievement.

## Selecting several

**Select** turns every card into a checkbox, and **Select all** picks
everything the search is showing. With some chosen you can:

- **Set date** on all of them at once;
- **Detect dates** to work each one out again from its file;
- **Use achievement dates** for files tied to an unlocked achievement;
- tie them all to one achievement;
- delete them together.

## Editing a file

The edit button on a card (or clicking the card of a save or doc) opens one
dialog with everything about that file:

| Field | Notes |
| --- | --- |
| Title | A name that is only used in the app. The file keeps its own name, which stays visible under the title. |
| Note | Free text. |
| Tags | Type a tag and press Enter or a comma. |
| Date | When it was really taken. See below. |
| Achievement | Ties the file to one of the game's achievements. |
| Account | For games with accounts (for example an OSRS profile), which account it belongs to. |

### Dates

A file's own modified date is often wrong, because copying or syncing gives
every file the day you moved it. So the app works out when a screenshot or
clip was taken from the most trustworthy place available, in this order:

1. the file's own data (photo EXIF or PNG creation time, or a video's creation
   time);
2. the file name (Steam, PlayStation, Xbox, NVIDIA and most capture tools put
   the time in it);
3. the file's modified date as your browser reports it;
4. the moment you uploaded it.

The dialog says where the date came from, so you can tell a fact from a guess.
**Detect from file** works the date out again, and you can always type your
own. When you tie a file to an achievement, you can choose to take the
achievement's unlock date as the file's date (**Tying also sets the date**).

## Copying and downloading

Every card can copy a link to its file or download it. Saves download their
latest version, and the edit dialog lists every version so you can download an
older one, add a new one, or delete one you no longer want.

## Deleting

Deleting moves a file to the trash. **Deleted (N)** at the top of the tab shows
what is in it, and a file can be restored from there. Files stay in the trash
for 7 days and are then removed for good.
