export interface ShortcutGroup {
  title: string;
  shortcuts: { keys: string; label: string }[];
}

// One list for both the `?` overlay and Settings → Keyboard Shortcuts, so
// the two can never disagree about what a key does.
export const SHORTCUT_GROUPS: ShortcutGroup[] = [
  {
    title: "Library",
    shortcuts: [
      { keys: "/", label: "Focus search" },
      { keys: "n", label: "Add a game" },
      { keys: "j / k or ↓ / ↑", label: "Move selection (List + preview view)" },
      {
        keys: "← ↑ → ↓, Enter",
        label: "Move focus between cards, open the focused one (Cards view)",
      },
      {
        keys: "a–z",
        label: "Jump to the first game starting with that letter (Cards view)",
      },
      { keys: "Esc", label: "Clear search, close panels" },
    ],
  },
  {
    title: "Game page",
    shortcuts: [
      {
        keys: "j / k",
        label: "Next / previous game (from the library you came from)",
      },
    ],
  },
  {
    title: "Anywhere",
    shortcuts: [
      {
        keys: "Ctrl/Cmd + K",
        label: "Jump to a game, collection, or settings section",
      },
      { keys: "?", label: "Show the shortcuts list" },
      { keys: "Esc", label: "Close the notification or profile menu" },
    ],
  },
];
