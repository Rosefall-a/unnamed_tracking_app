# Game library imports

Settings › Metadata › Achievements & Accounts connects game store accounts and
imports what you own into the Games library. Each imported game is tagged with
its store and put in a collection of the same name. Settings › Connections
lists the connected accounts, how many games each has brought in and when it
last synced, with a **Sync now** button.

A re-import updates playtime and achievements and never changes a status you
set. A game that has left the account (refunded, removed from a family share)
is flagged as missing rather than deleted.

## Steam

Needs two things:

- **Profile link or ID**: paste your profile's link
  (`steamcommunity.com/id/yourname` or `steamcommunity.com/profiles/7656…`),
  the name after `/id/`, or your SteamID in any of its usual forms
  (`7656…`, `STEAM_0:1:…`, `[U:1:…]`).
- **Web API key**, from <https://steamcommunity.com/dev/apikey>.

In Steam, set Profile › Privacy Settings › **Game details** to Public. Steam
otherwise does not share your games; connecting then says so instead of
importing an empty library.

An import saves your owned games first, then reads their achievements a few
games at a time, then adds each new game's store details, tags and artwork.
The progress shows which step it is on. Turn on **Import Steam wishlist** under
Settings › Metadata › Scan & providers to add your wishlist as Wishlist games.

## Epic Games

Epic has no public API for libraries, so this uses the same sign-in as the
open-source Epic launchers (Legendary, Heroic). It is unofficial and may stop
working if Epic changes it.

1. On the Epic Games card, open **Sign in to Epic Games**.
2. After signing in, Epic shows a short block of text. Copy the
   `authorizationCode` value, or the whole page.
3. Paste it into **Authorization code** and press **Connect** within a few
   minutes. A code works only once.

The app keeps only the resulting sign-in token, encrypted, never your password.
If an import later says the sign-in has expired, disconnect and connect again
with a new code.

An import adds your owned games with their title, description, developer,
publisher and box art, plus playtime. DLC, add-ons and Unreal Engine
marketplace items are skipped. Epic does not offer achievements to this
sign-in, so none are imported.
