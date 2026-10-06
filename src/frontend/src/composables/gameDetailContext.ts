import { inject, type InjectionKey } from "vue";
import type { useGameDetail } from "./useGameDetail";
export const gameDetailKey: InjectionKey<ReturnType<typeof useGameDetail>> =
  Symbol("Game detail");
export function useGameDetailContext() {
  const context = inject(gameDetailKey);
  if (!context) throw new Error("Game detail context is missing.");
  return context;
}
