import { NAVIGATION_SHORTCUTS } from "./shortcuts";

export type TourShortcut = "search" | "games" | "media" | "settings" | "help";
export interface QuickTourStep {
  id: string;
  title: string;
  description: string;
  target: string;
  path?: string;
  destination?: string;
  shortcut?: TourShortcut;
  openedTarget?: string;
  requirement: "read" | "navigate" | "shortcut" | "open-close";
}

const fallback = ', [data-tour="open-menu"], .home-shortcuts';
export function quickTourSteps(touch: boolean): QuickTourStep[] {
  return [
    {
      id: "welcome",
      title: "Explore your library",
      description:
        "This tour uses your real pages and controls. You can skip a step or end at any time. Nothing is created for you.",
      path: "/",
      target: ".home-shortcuts, #main-content",
      requirement: "read",
    },
    {
      id: "search",
      title: "Find something quickly",
      description: touch
        ? "Open Search, try a title or a page name, then close the dialog. Search is also in the hamburger menu."
        : "Press Ctrl/Cmd + K to open Search. Try a title or a page name, then press Escape to close it.",
      target: '[data-tour="open-search"]' + fallback,
      openedTarget: '[data-tour="palette-search"]',
      path: "/",
      shortcut: "search",
      requirement: touch ? "open-close" : "shortcut",
    },
    {
      id: "games",
      title: "Open All games",
      description: touch
        ? "Tap Games in the bottom bar to open All games."
        : "Try Alt + G now. It opens All games from anywhere outside a dialog or text field.",
      target: '[data-tour="nav-games"]' + fallback,
      destination: "/games",
      shortcut: "games",
      requirement: touch ? "navigate" : "shortcut",
    },
    {
      id: "filters",
      title: "Explore game filters",
      description:
        "Open Filters to see platforms, genres and advanced options, then close the panel. Presets let you reuse combinations later.",
      path: "/games",
      target: '[data-tour="games-filters"]',
      openedTarget: '[data-tour="games-filter-panel"] .filter-group',
      requirement: "open-close",
    },
    {
      id: "collections",
      title: "Make a collection",
      description:
        "Open Create Collection to explore Manual and Smart collections, then close the dialog. You do not need to save anything for the tour.",
      path: "/collections",
      target: '[data-tour="collection-create"]',
      openedTarget: 'dialog[data-tour="collection-editor"][open] .kind-pick',
      requirement: "open-close",
    },
    {
      id: "media",
      title: "Switch to your media",
      description: touch
        ? "Tap Media in the bottom bar. It opens Movies; the top bar also offers TV, Anime and Lists."
        : "Try Alt + M to open Movies. The top bar also offers TV, Anime and Lists.",
      target: '[data-tour="nav-media"]' + fallback,
      destination: "/movies",
      shortcut: "media",
      requirement: touch ? "navigate" : "shortcut",
    },
    {
      id: "settings",
      title: "Open your preferences",
      description: touch
        ? "Tap Settings in the bottom bar to open your preferences."
        : "Try Alt + P to open Settings. Account, preferences and administration have their own areas.",
      target: '[data-tour="nav-settings"]' + fallback,
      destination: "/settings",
      shortcut: "settings",
      requirement: touch ? "navigate" : "shortcut",
    },
    {
      id: "appearance",
      title: "Choose your appearance",
      description:
        "Light, Dark and System share the same controls. Explore palettes, spacing and navigation here. Changes you choose are saved to your account.",
      path: "/settings?section=appearance",
      target: '[data-tour="ui-appearance"]',
      requirement: "read",
    },
    {
      id: "home",
      title: "Customize Home",
      description:
        "Open Customize Home. Choose widgets on one side and arrange them on the other on wider screens, then close the dialog. Saving is optional for this tour.",
      path: "/",
      target: '[data-tour="customize-home"]',
      openedTarget:
        'dialog[data-tour="home-widget-editor"][open] #widget-selection-heading',
      requirement: "open-close",
    },
    {
      id: "help",
      title: "Keep shortcuts close",
      description: touch
        ? "Open shortcut help and expand a section, then close it. The current page comes first. You can replay this tour from Home or shortcut settings."
        : "Press ? to open shortcut help. Expand a section, then press Escape to close it. The current page comes first; replay this tour from Home or shortcut settings.",
      path: "/games",
      target: '[data-tour="nav-games"]' + fallback,
      openedTarget: 'dialog[data-tour="shortcut-help"][open] .shortcut-groups',
      shortcut: "help",
      requirement: touch ? "open-close" : "shortcut",
    },
  ];
}

export function matchesTourShortcut(
  shortcut: TourShortcut,
  event: {
    key: string;
    code?: string;
    altKey: boolean;
    ctrlKey: boolean;
    metaKey: boolean;
    shiftKey: boolean;
  },
): boolean {
  if (shortcut === "search")
    return (
      (event.ctrlKey || event.metaKey) &&
      !event.altKey &&
      !event.shiftKey &&
      event.key.toLowerCase() === "k"
    );
  if (shortcut === "help")
    return (
      event.key === "?" && !event.altKey && !event.ctrlKey && !event.metaKey
    );
  if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey)
    return false;
  const path = { games: "/games", media: "/movies", settings: "/settings" }[
    shortcut
  ];
  const key = /^[a-z]$/i.test(event.key)
    ? event.key.toLowerCase()
    : /^Key[A-Z]$/.test(event.code || "")
      ? event.code!.slice(3).toLowerCase()
      : "";
  return NAVIGATION_SHORTCUTS.some(
    (item) => item.path === path && item.key === key,
  );
}
