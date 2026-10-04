export interface HomeWidgetChoice {
  id: string;
  title: string;
  description: string;
  available?: boolean;
}

export const CORE_HOME_WIDGETS: HomeWidgetChoice[] = [
  {
    id: "continue-playing",
    title: "Continue playing",
    description: "Your games in progress, most recently played first.",
  },
  {
    id: "recently-added",
    title: "Recently added",
    description: "The newest games in your library.",
  },
  {
    id: "library-summary",
    title: "Library summary",
    description: "Game, favorite and collection counts.",
  },
  {
    id: "goals",
    title: "Goals & bounties",
    description: "Your active personal goals.",
  },
  {
    id: "random-picker",
    title: "Random picker",
    description: "Choose a game with your own filters.",
  },
  {
    id: "weekly-digest",
    title: "This week",
    description:
      "Games played, achievements, completed goals and metadata activity.",
  },
  {
    id: "backlog",
    title: "Revisit your backlog",
    description: "Games added over 90 days ago that you have not played.",
  },
  {
    id: "on-this-day",
    title: "On this day",
    description: "Games added on this date in previous years.",
  },
  {
    id: "getting-started",
    title: "Getting started",
    description: "Connect a library, favorite a game and set a goal.",
  },
];

export function selectedHomeWidgets(
  ids: string[],
  choices: HomeWidgetChoice[],
): HomeWidgetChoice[] {
  const available = new Map(choices.map((choice) => [choice.id, choice]));
  return ids.map(
    (id) =>
      available.get(id) ?? {
        id,
        title: id.startsWith("collection:")
          ? id.slice(11)
          : "Unavailable widget",
        description:
          "This widget is unavailable. Your selection is retained until it returns or you remove it.",
        available: false,
      },
  );
}
