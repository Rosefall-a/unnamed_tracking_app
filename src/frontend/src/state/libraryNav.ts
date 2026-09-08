// Tracks the order of games last shown in the library grid/list, so
// GameDetail's J/K shortcuts can step to the next/prev game without going
// back to the grid first. Populated by GameLibrary.vue on every load;
// simply a no-op for a game opened any other way (a bookmark, a direct
// link, Home Hub) since there's no "current list" to step through.
import { ref } from 'vue'

const order = ref<string[]>([])

export function setLibraryNavOrder(ids: string[]) {
  order.value = ids
}

export function peekAdjacentGameId(currentId: string, direction: -1 | 1): string | null {
  const ids = order.value
  const index = ids.indexOf(currentId)
  if (index === -1) return null
  const next = index + direction
  if (next < 0 || next >= ids.length) return null
  return ids[next]
}
