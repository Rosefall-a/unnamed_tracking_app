// Set aside for one game: small changes that leave everything else on
// the game as it is (the full edit form never sends these fields).
import { mockGames } from "../data/mockGames";
import { failedRequest } from "./apiError";
import { invalidateGameList, mapBackendGame, rememberGame } from "./games";
import type { BackendGame } from "./games";
import type { Game, SetAsideReason } from "../types/game";

// Set a game aside (out of the library tabs, Home and counts, nothing deleted)
// or bring it back.
export async function setGameSetAside(
  gameId: string,
  setAside: boolean,
  reason: SetAsideReason | null = null,
): Promise<Game> {
  return patchGameFields(gameId, {
    set_aside: setAside,
    ...(setAside ? { set_aside_reason: reason } : {}),
  });
}

async function patchGameFields(
  gameId: string,
  body: Record<string, unknown>,
): Promise<Game> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    const index = mockGames.findIndex((g) => g.id === gameId);
    if (index === -1) throw new Error(`Game ${gameId} not found`);
    const g = { ...mockGames[index] };
    if ("set_aside" in body) {
      g.setAsideAt = body.set_aside
        ? (g.setAsideAt ?? new Date().toISOString())
        : null;
      g.setAsideReason = body.set_aside
        ? ((body.set_aside_reason as SetAsideReason | null) ?? null)
        : null;
    }
    mockGames[index] = g;
    return g;
  }
  const response = await fetch(`/api/game/update/${gameId}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw await failedRequest(response);
  const raw: BackendGame = await response.json();
  invalidateGameList();
  return rememberGame(mapBackendGame(raw));
}
