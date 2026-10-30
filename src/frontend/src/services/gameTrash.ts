import { invalidateGameList } from "./games";

// deleteGame is a soft-delete (see the backend route), restorable for 7
// days via these, same pattern as game archives/inbox media
export interface TrashedGame {
  id: string;
  title: string;
  deleted_at: number;
  purge_at: number;
}

export async function fetchGameTrash(): Promise<TrashedGame[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") return [];
  const response = await fetch("/api/game/trash", { credentials: "include" });
  if (!response.ok)
    throw new Error(
      `Could not fetch game trash: ${response.status} ${response.statusText}`,
    );
  return await response.json();
}

export async function restoreGame(gameId: string): Promise<void> {
  const response = await fetch(`/api/game/${gameId}/restore`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Could not restore game: ${response.status} ${response.statusText} ${message}`,
    );
  }
  invalidateGameList();
}
