# Your Home

Home starts with a quiet welcome and links to your library. It does not open a welcome tour automatically. **Quick tour** remains available whenever you want an introduction.

The guided tour takes you through Search, All games and its filters, collection creation, Movies, appearance settings, Home widgets and shortcut help. It highlights the real controls and follows you into their dialogs. On desktop, practice **Ctrl/Cmd + K**, **Alt + G**, **Alt + M**, **Alt + P** and **?** to complete the shortcut steps. Touch screens offer tap controls for the same tasks. Close each demonstrated dialog before continuing; creating or saving content is optional. You can go back, skip a step or end the tour at any time.

On first sign-in, **Save & take a tour** saves your appearance choices and starts the tour. **Save & continue** saves them without starting it. Replay later from Home or **Preferences → Keyboard shortcuts**.

Choose **Add widgets** or **Customize Home** to select what appears. Use the up/down buttons to set the order, or Remove to take a widget off Home. **Save Home** stores the selection and order on your account, across devices. Cancel leaves the saved layout unchanged. If a save fails, the chooser keeps your draft and shows an error; reconnect and save again.

## Available widgets

| Widget | What it shows |
| --- | --- |
| Continue playing | Games in progress, most recently played first |
| Recently added | Your newest games |
| Library summary | Game, favorite and collection counts |
| Goals & bounties | Active personal goals provided by the enabled Collector's Archive plugin |
| Random picker | Your existing status/platform/genre/length/priority picker |
| This week | Recorded game activity, achievements, completed goals and metadata changes over seven days |
| Revisit your backlog | Games added over 90 days ago without recorded play |
| On this day | Games added on this date in earlier years |
| Getting started | Connect a library, favorite a game and set a goal |
| Collection shelves | A shelf for each of your game collections |

Game shelves retain editing, favorites, status changes and collection actions. They scroll horizontally by touch or with the arrow buttons. Core widgets show loading and retry states when their data is unavailable.

Active plugins with approved Home contributions also appear in the chooser. They are optional. If a plugin is disabled or removed, its widget displays an unavailable state and its selection stays saved. The widget can return when its contribution becomes available again. Remove it from the chooser to forget the selection.

A granted plugin page replacement can still replace Home. If the native replacement fails, the host Home remains available. See the [plugin UI contract](../development/plugin-ui.md) for native widgets and the [development checkpoint](../development/ui-redevelopment.md) for migration details.

The former weekly-digest interface toggle is now the **This week** widget. Home shelf visibility and onboarding are managed through this chooser; the original library features remain available from navigation regardless of your widget choices.
