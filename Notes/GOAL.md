## Game Data

The web app should aim to store as much information related to a game as reasonably possible.

A game should not be limited to basic tracking information such as playtime or completion status. The web app should act as a central repository for the user's history and data associated with each game.

This may include:

* Game metadata
* Playtime
* Last played date
* First played date
* Completion status
* Progress
* Ratings
* Reviews
* Notes
* Tags
* Screenshots
* Videos or other captured media
* Save files
* Save backups
* Game-specific files
* Achievements
* DLC
* Mods
* Mod configurations
* Settings
* Control configurations
* Game versions
* Installation information
* Launcher/platform information
* External IDs
* Cover art and other artwork
* User-created content
* Other information provided by supported integrations

### Game as a Centralized Record

Each game should have a centralized record in the web app containing the information collected from all supported sources.

For example, information about a game may come from:

* Playnite
* Steam
* Other game launchers
* External game databases
* Manual user input
* Other future integrations

The web app should combine this information into a single game record rather than maintaining completely separate records for each integration.

### Files and Backups

The web app should support storing files associated with games where practical.

This includes things such as screenshots, save files, configuration files, and backups.

Files should be associated with the appropriate user and game and should remain available independently of the integration that originally uploaded them.

For example, if a save file was uploaded through the Playnite plugin, uninstalling the Playnite plugin should not remove that save from the web app.

Where appropriate, the system should retain information about:

* When a file was created
* When it was uploaded
* Where it originated
* Which game it belongs to
* Which platform or launcher it came from
* Which version of the game it corresponds to
* Whether it is a backup or current file
* Any other metadata necessary to identify and restore it

### Long-Term Data Preservation

The project should prioritize preserving a user's game history and data over the lifetime of the project.

Integrations should be considered data collectors and synchronization clients. They should not be the only place where important user data exists.

The web app should retain synchronized data even if:

* An integration is uninstalled.
* A launcher is no longer used.
* A game is removed from a launcher.
* A game is moved to another platform.
* An integration becomes unavailable.
* The user changes computers.

The goal is for the web app to become a **centralized personal archive of everything related to the user's games**, rather than simply being a website that displays statistics.
