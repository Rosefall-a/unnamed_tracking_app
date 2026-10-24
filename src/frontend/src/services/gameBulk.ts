import { mockGames } from "../data/mockGames";
import { failedRequest } from "./apiError";
import { denormalizeStatus, forgetGame, invalidateGameList } from "./games";
import type { GameStatus } from "../types/game";

export interface BulkEditFields {
  status?: GameStatus;
  favorite?: boolean;
  developer?: string | null;
  publisher?: string | null;
  series?: string | null;
  ageRating?: string | null;
  platform?: string | null;
  priority?: string | null;
  tags?: string[];
  features?: string[];
}

export async function bulkUpdateGames(
  gameIds: string[],
  fields: BulkEditFields,
): Promise<number> {
  const payload: Record<string, unknown> = { game_ids: gameIds };
  if (fields.status !== undefined)
    payload.status = denormalizeStatus(fields.status);
  if (fields.favorite !== undefined) payload.favorite = fields.favorite;
  if (fields.developer !== undefined) payload.developer = fields.developer;
  if (fields.publisher !== undefined) payload.publisher = fields.publisher;
  if (fields.series !== undefined) payload.series = fields.series;
  if (fields.ageRating !== undefined) payload.age_rating = fields.ageRating;
  if (fields.platform !== undefined) payload.platform = fields.platform;
  if (fields.priority !== undefined) payload.priority = fields.priority;
  if (fields.tags !== undefined) payload.tags = fields.tags;
  if (fields.features !== undefined) payload.features = fields.features;

  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    let count = 0;
    for (const game of mockGames) {
      if (!gameIds.includes(game.id)) continue;
      if (fields.status !== undefined) game.status = fields.status;
      if (fields.favorite !== undefined) game.favorite = fields.favorite;
      if (fields.developer !== undefined) game.developer = fields.developer;
      if (fields.publisher !== undefined) game.publisher = fields.publisher;
      if (fields.series !== undefined) game.series = fields.series;
      if (fields.ageRating !== undefined) game.ageRating = fields.ageRating;
      if (fields.tags !== undefined) game.tags = fields.tags;
      if (fields.features !== undefined) game.features = fields.features;
      count++;
    }
    return count;
  }

  const response = await fetch("/api/game/bulk-update", {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await failedRequest(response);
  const result: { updated: number } = await response.json();
  invalidateGameList();
  return result.updated;
}

export async function bulkDeleteGames(gameIds: string[]): Promise<number> {
  const response = await fetch("/api/game/bulk-delete", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ game_ids: gameIds }),
  });
  if (!response.ok) throw await failedRequest(response);
  const result: { deleted: number } = await response.json();
  for (const id of gameIds) forgetGame(id);
  return result.deleted;
}
