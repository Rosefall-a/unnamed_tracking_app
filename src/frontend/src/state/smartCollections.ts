// Rule-based ("smart") collections, membership is computed live against
// whatever the library looks like right now, instead of being a stored
// list of game ids. Rules live in localStorage, same tier as manual
// collections (Collections.vue's manualCollectionNames) since neither has
// a backend row of its own.
import { ref } from 'vue'
import type { Game } from '../types/game'

export type SmartField = 'status' | 'playtime_hours' | 'favorite' | 'tag' | 'source'

export interface SmartCollection {
  id: string
  name: string
  field: SmartField
  // unused for 'favorite'; a GameStatus value for 'status'; free text for
  // 'tag'/'source'; a number-as-string (hours) for 'playtime_hours'
  value: string
}

const STORAGE_KEY = 'smartCollections'

function load(): SmartCollection[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as SmartCollection[]) : []
  } catch {
    return []
  }
}

export const smartCollections = ref<SmartCollection[]>(load())

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(smartCollections.value))
  } catch {
    // best-effort, the rule just won't survive a reload
  }
}

export function addSmartCollection(entry: Omit<SmartCollection, 'id'>): string {
  const id = crypto.randomUUID()
  smartCollections.value = [...smartCollections.value, { ...entry, id }]
  persist()
  return id
}

export function removeSmartCollection(id: string) {
  smartCollections.value = smartCollections.value.filter((c) => c.id !== id)
  persist()
}

export function findSmartCollectionByName(name: string): SmartCollection | undefined {
  return smartCollections.value.find((c) => c.name === name)
}

export function matchesSmartCollection(game: Game, rule: SmartCollection): boolean {
  switch (rule.field) {
    case 'status':
      return game.status === rule.value
    case 'favorite':
      return game.favorite === true
    case 'source':
      return (game.source ?? '').toLowerCase() === rule.value.toLowerCase()
    case 'tag':
      return game.tags.some((t) => t.toLowerCase() === rule.value.toLowerCase())
    case 'playtime_hours': {
      const totalMinutes = game.platforms.reduce((sum, p) => sum + p.playtimeMinutes, 0)
      return totalMinutes / 60 > Number(rule.value)
    }
    default:
      return false
  }
}

export const SMART_FIELD_LABELS: Record<SmartField, string> = {
  status: 'Status is',
  playtime_hours: 'Playtime over (hours)',
  favorite: 'Favorited',
  tag: 'Tag is',
  source: 'Source is',
}

export function describeSmartCollection(rule: SmartCollection): string {
  if (rule.field === 'favorite') return 'Favorited'
  if (rule.field === 'playtime_hours') return `Playtime over ${rule.value}h`
  return `${SMART_FIELD_LABELS[rule.field]} "${rule.value}"`
}
