<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import CollectionCard from '../components/CollectionCard.vue'
import { fetchGames } from '../services/games'
import type { Game } from '../types/game'
import { currentUser } from '../state/auth'

type SortBy = 'name' | 'count'

const router = useRouter()

const games = ref<Game[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const searchQuery = ref('')
const sortBy = ref<SortBy>('name')

// Empty collections (no games assigned yet) have nowhere to live on the
// backend, so they're tracked locally until a game is actually added to them.
const MANUAL_COLLECTIONS_KEY = 'manualCollections'
const manualCollectionNames = ref<string[]>(loadManualCollections())

function loadManualCollections(): string[] {
  try {
    const raw = localStorage.getItem(MANUAL_COLLECTIONS_KEY)
    return raw ? (JSON.parse(raw) as string[]) : []
  } catch {
    return []
  }
}

function saveManualCollections() {
  localStorage.setItem(MANUAL_COLLECTIONS_KEY, JSON.stringify(manualCollectionNames.value))
}

function createCollection() {
  const name = window.prompt('Name your new collection:')
  if (!name || !name.trim()) return
  const trimmed = name.trim()
  const alreadyExists = collectionSummaries.value.some((c) => c.name.toLowerCase() === trimmed.toLowerCase())
  if (alreadyExists) {
    window.alert(`"${trimmed}" already exists.`)
    return
  }
  manualCollectionNames.value.push(trimmed)
  saveManualCollections()
}

async function loadGames() {
  loading.value = true
  try {
    games.value = await fetchGames()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load games'
  } finally {
    loading.value = false
  }
}

onMounted(loadGames)

interface CollectionSummary {
  name: string
  games: Game[]
}

const collectionSummaries = computed<CollectionSummary[]>(() => {
  const map = new Map<string, Game[]>()
  for (const g of games.value) {
    for (const c of g.collections) {
      if (!map.has(c)) map.set(c, [])
      map.get(c)!.push(g)
    }
  }
  for (const name of manualCollectionNames.value) {
    if (!map.has(name)) map.set(name, [])
  }
  return Array.from(map.entries()).map(([name, list]) => ({ name, games: list }))
})

const filteredCollections = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  let result = collectionSummaries.value
  if (q) {
    result = result.filter((c) => c.name.toLowerCase().includes(q))
  }
  return [...result].sort((a, b) => {
    if (sortBy.value === 'count') return b.games.length - a.games.length
    return a.name.localeCompare(b.name)
  })
})

function openCollection(name: string) {
  router.push(`/collections/${encodeURIComponent(name)}`)
}
</script>

<template>
  <main class="collections-page">
    <div v-if="currentUser" class="profile-chip">
      <span class="profile-name">{{ currentUser.username }}</span>
      <div class="profile-avatar">{{ currentUser.username.slice(0, 2).toUpperCase() }}</div>
    </div>

    <div class="content">
      <div class="header-row">
        <h1>Collections</h1>
        <div class="header-actions">
          <input v-model="searchQuery" type="text" class="search-input" placeholder="Search collections…" />
          <select v-model="sortBy" class="filter-select">
            <option value="name">Name</option>
            <option value="count">Most Games</option>
          </select>
          <button type="button" class="add-button" @click="createCollection">+ Create Collection</button>
        </div>
      </div>

      <p v-if="loading">Loading…</p>
      <p v-else-if="error" class="error">{{ error }}</p>

      <template v-else>
        <div v-if="filteredCollections.length" class="grid">
          <CollectionCard
            v-for="col in filteredCollections"
            :key="col.name"
            :name="col.name"
            :games="col.games"
            @open="openCollection"
          />
        </div>
        <p v-else class="empty-row">
          No collections yet — create one above, or use a game's collection button to start one.
        </p>
      </template>
    </div>
  </main>
</template>

<style scoped>
.collections-page {
  position: relative;
  padding: 84px 24px 24px;
  font-family: system-ui, sans-serif;
  background: #121212;
  min-height: 100vh;
  color: #fff;
}
.profile-chip {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(20, 20, 20, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border-radius: 999px;
  padding: 6px 6px 6px 16px;
}
.profile-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #d68a34;
  color: #111;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}
.profile-name {
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}
.header-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.header-row h1 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 700;
}
.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.search-input,
.filter-select {
  height: 40px;
  box-sizing: border-box;
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 0 14px;
  font: inherit;
  font-size: 13px;
  transition: border-color 0.15s ease;
}
.search-input {
  width: 220px;
}
.search-input:focus,
.filter-select:focus {
  outline: none;
  border-color: #d68a34;
}
.filter-select:hover {
  border-color: #4a4a4a;
}
.filter-select {
  appearance: none;
  -webkit-appearance: none;
  padding-right: 34px;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path d='M1 1l4 4 4-4' stroke='%23999' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>");
  background-repeat: no-repeat;
  background-position: right 16px center;
}
.add-button {
  height: 40px;
  box-sizing: border-box;
  background: #d68a34;
  color: #111;
  border: none;
  border-radius: 8px;
  padding: 0 18px;
  font-weight: 600;
  cursor: pointer;
}
/* fixed 10-per-row grid — column width only depends on the container, never
   on how many collections there are, so adding one more just starts filling
   the next row instead of resizing every existing card */
.grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 16px;
}
.grid :deep(.collection-card-wrap) {
  width: auto;
  min-width: 0;
}
.empty-row {
  color: #777;
  font-size: 14px;
}
.error {
  color: #f87171;
}
</style>
