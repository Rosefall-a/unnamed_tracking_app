<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import GameCard from '../components/GameCard.vue'
import GameFormModal from '../components/GameFormModal.vue'
import { fetchGames, deleteGame, addGameToCollection } from '../services/games'
import type { Game } from '../types/game'

const games = ref<Game[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const showFormModal = ref(false)
const editingGame = ref<Game | null>(null)

const deletingGame = ref<Game | null>(null)
const deleting = ref(false)
const deleteError = ref<string | null>(null)

const bgLayers = ref<{ url: string | null; visible: boolean }[]>([
  { url: null, visible: false },
  { url: null, visible: false },
])
const activeLayer = ref(0)

function setHoverImage(url: string | null) {
  if (url === null) {
    bgLayers.value[activeLayer.value].visible = false
    return
  }
  const nextLayer = activeLayer.value === 0 ? 1 : 0
  bgLayers.value[nextLayer] = { url, visible: true }
  bgLayers.value[activeLayer.value].visible = false
  activeLayer.value = nextLayer
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

function openEditModal(game: Game) {
  editingGame.value = game
  showFormModal.value = true
}

async function onGameSaved() {
  showFormModal.value = false
  editingGame.value = null
  await loadGames()
}

function requestDelete(game: Game) {
  deletingGame.value = game
  deleteError.value = null
}

async function confirmDelete() {
  if (!deletingGame.value) return
  deleting.value = true
  deleteError.value = null
  try {
    await deleteGame(deletingGame.value.id)
    deletingGame.value = null
    await loadGames()
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : 'Failed to delete game'
  } finally {
    deleting.value = false
  }
}

// crude placeholder — a proper picker UI can replace this once Collections
// has more than one feature built for it
async function handleAddToCollection(game: Game) {
  const name = window.prompt(`Add "${game.title}" to which collection?`)
  if (!name || !name.trim()) return
  try {
    await addGameToCollection(game.id, name.trim())
    await loadGames()
  } catch (err) {
    window.alert(err instanceof Error ? err.message : 'Failed to add to collection')
  }
}

const playingGames = computed(() => games.value.filter((g) => g.status === 'playing'))

const recentlyAdded = computed(() =>
  [...games.value]
    .filter((g) => g.dateAdded)
    .sort((a, b) => (b.dateAdded! > a.dateAdded! ? 1 : -1))
    .slice(0, 10),
)

const collectionGroups = computed(() => {
  const map = new Map<string, Game[]>()
  for (const g of games.value) {
    for (const c of g.collections) {
      if (!map.has(c)) map.set(c, [])
      map.get(c)!.push(g)
    }
  }
  return Array.from(map.entries()).map(([name, list]) => ({ name, games: list }))
})
</script>

<template>
  <main class="home">
    <div
      v-for="(layer, i) in bgLayers"
      :key="i"
      class="ambient-bg"
      :class="{ visible: layer.visible }"
      :style="layer.url ? { backgroundImage: `url(${layer.url})` } : {}"
    ></div>

    <div class="content">
      <h1>Home</h1>
      <p v-if="loading">Loading…</p>
      <p v-else-if="error" class="error">{{ error }}</p>

      <template v-else>
        <section class="row">
          <h2>Continue Playing</h2>
          <div v-if="playingGames.length" class="shelf">
            <GameCard
              v-for="game in playingGames"
              :key="game.id"
              :game="game"
              @hover="setHoverImage"
              @edit="openEditModal"
              @delete="requestDelete"
              @add-to-collection="handleAddToCollection"
            />
          </div>
          <p v-else class="empty-row">Nothing in progress right now.</p>
        </section>

        <section class="row">
          <h2>Recently Added</h2>
          <div v-if="recentlyAdded.length" class="shelf">
            <GameCard
              v-for="game in recentlyAdded"
              :key="game.id"
              :game="game"
              @hover="setHoverImage"
              @edit="openEditModal"
              @delete="requestDelete"
              @add-to-collection="handleAddToCollection"
            />
          </div>
          <p v-else class="empty-row">No games added yet.</p>
        </section>

        <section v-for="group in collectionGroups" :key="group.name" class="row">
          <h2>{{ group.name }}</h2>
          <div class="shelf">
            <GameCard
              v-for="game in group.games"
              :key="game.id"
              :game="game"
              @hover="setHoverImage"
              @edit="openEditModal"
              @delete="requestDelete"
              @add-to-collection="handleAddToCollection"
            />
          </div>
        </section>
        <p v-if="!collectionGroups.length" class="empty-row">
          No collections yet — use a card's collection button to start one.
        </p>
      </template>

      <GameFormModal
        v-if="showFormModal"
        :game="editingGame"
        @close="showFormModal = false"
        @saved="onGameSaved"
      />

      <div v-if="deletingGame" class="confirm-backdrop" @click.self="deletingGame = null">
        <div class="confirm-dialog">
          <h3>Delete {{ deletingGame.title }}?</h3>
          <p>This can't be undone.</p>
          <div v-if="deleteError" class="confirm-error">{{ deleteError }}</div>
          <div class="confirm-actions">
            <button type="button" class="secondary-button" @click="deletingGame = null">Cancel</button>
            <button type="button" class="danger-button" :disabled="deleting" @click="confirmDelete">
              {{ deleting ? 'Deleting…' : 'Delete' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.home {
  position: relative;
  padding: 84px 24px 24px;
  font-family: system-ui, sans-serif;
  background: #121212;
  min-height: 100vh;
  color: #fff;
  overflow: hidden;
}
.ambient-bg {
  position: fixed;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: blur(90px);
  opacity: 0;
  transform: scale(1.2);
  transition: opacity 0.6s ease;
  z-index: 0;
}
.ambient-bg.visible {
  opacity: 0.35;
}
.content {
  position: relative;
  z-index: 1;
}
.row {
  margin-bottom: 32px;
}
.row h2 {
  font-size: 1.1rem;
  margin: 0 0 12px;
}
.shelf {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding: 20px 4px 28px;
}
.empty-row {
  color: #777;
  font-size: 14px;
  margin: 0;
}
.error {
  color: #f87171;
}
.confirm-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
}
.confirm-dialog {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 22px;
  width: 100%;
  max-width: 360px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
}
.confirm-dialog h3 {
  margin: 0 0 8px;
}
.confirm-dialog p {
  margin: 0 0 16px;
  color: #aaa;
  font-size: 14px;
}
.confirm-error {
  color: #fca5a5;
  font-size: 13px;
  margin-bottom: 12px;
}
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.secondary-button,
.danger-button {
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 600;
  cursor: pointer;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.danger-button {
  background: #dc2626;
  color: #fff;
}
.danger-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>