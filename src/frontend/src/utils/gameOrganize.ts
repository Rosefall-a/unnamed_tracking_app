// Set aside: what keeps a backlog manageable. A set-aside game is kept with
// everything it has but stays out of the library tabs, Home and counts.
import type { Game, SetAsideReason } from "../types/game";

export const SET_ASIDE_REASONS: {
  id: SetAsideReason;
  label: string;
  hint: string;
}[] = [
  {
    id: "not_a_game",
    label: "Not a real game",
    hint: "Books, soundtracks, tools, test servers, playtests, demos",
  },
  {
    id: "online_only",
    label: "Online only",
    hint: "Needs servers or other players, or the servers are gone",
  },
  {
    id: "not_interested",
    label: "Not interested",
    hint: "Came in a bundle, or you will never play it",
  },
  { id: "other", label: "Other", hint: "Anything else" },
];

export function isSetAside(g: Pick<Game, "setAsideAt">): boolean {
  return !!g.setAsideAt;
}

export function reasonLabel(reason: SetAsideReason | null | undefined): string {
  return SET_ASIDE_REASONS.find((r) => r.id === reason)?.label ?? "Set aside";
}
