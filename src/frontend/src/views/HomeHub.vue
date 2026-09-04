<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import GameCard from '../components/GameCard.vue'
import GameFormModal from '../components/GameFormModal.vue'
import { fetchGames, deleteGame } from '../services/games'
import CollectionPickerModal from '../components/CollectionPickerModal.vue'
import type { Game } from '../types/game'
import { currentUser } from '../state/auth'

const router = useRouter()

const games = ref<Game[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const showFormModal = ref(false)
const editingGame = ref<Game | null>(null)

const deletingGame = ref<Game | null>(null)
const deleting = ref(false)
const deleteError = ref<string | null>(null)

const totalGames = computed(() => games.value.length)
const favoriteCount = computed(() => games.value.filter((g) => g.favorite).length)

const bgLayers = ref<{ url: string | null; visible: boolean }[]>([
  { url: null, visible: false },
  { url: null, visible: false },
])
const activeLayer = ref(0)

// only crossfade once the cursor has settled on a card briefly — gliding
// across many cards shouldn't flicker the ambient background
let hoverDebounceTimer: ReturnType<typeof setTimeout> | null = null

function setHoverImage(url: string | null) {
  if (hoverDebounceTimer) clearTimeout(hoverDebounceTimer)
  hoverDebounceTimer = setTimeout(() => {
    if (url === null) {
      bgLayers.value[activeLayer.value].visible = false
      return
    }
    const nextLayer = activeLayer.value === 0 ? 1 : 0
    bgLayers.value[nextLayer] = { url, visible: true }
    bgLayers.value[activeLayer.value].visible = false
    activeLayer.value = nextLayer
  }, 400)
}

function pickRandomGame() {
  if (!games.value.length) return
  const random = games.value[Math.floor(Math.random() * games.value.length)]
  router.push(`/games/${random.id}`)
}

async function loadGames() {
  loading.value = true
  try {
    games.value = await fetchGames()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load games'
  } finally {
    loading.value = false
    await nextTick()
    updateAllShelfArrows()
  }
}

// toggles each arrow's visibility based on whether its shelf can actually
// scroll further that direction — no point showing a left arrow at scrollLeft 0
function updateShelfArrows(shelf: HTMLElement) {
  const wrap = shelf.closest('.shelf-wrap')
  if (!wrap) return
  const left = wrap.querySelector('.shelf-arrow.left')
  const right = wrap.querySelector('.shelf-arrow.right')
  const maxScroll = shelf.scrollWidth - shelf.clientWidth
  left?.classList.toggle('can-scroll', shelf.scrollLeft > 4)
  right?.classList.toggle('can-scroll', shelf.scrollLeft < maxScroll - 4)
}

function updateAllShelfArrows() {
  document.querySelectorAll<HTMLElement>('.shelf').forEach(updateShelfArrows)
}

window.addEventListener('resize', updateAllShelfArrows)
onUnmounted(() => window.removeEventListener('resize', updateAllShelfArrows))

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

function onDeleteFromModal(gameId: string) {
  const game = games.value.find((g) => g.id === gameId)
  showFormModal.value = false
  editingGame.value = null
  if (game) requestDelete(game)
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

const collectionPickerGame = ref<Game | null>(null)

function handleAddToCollection(game: Game) {
  collectionPickerGame.value = game
}

async function onCollectionAdded() {
  await loadGames()
}

const SHELF_CAP = 20

const playingGames = computed(() => games.value.filter((g) => g.status === 'playing').slice(0, SHELF_CAP))

const recentlyAdded = computed(() =>
  [...games.value]
    .filter((g) => g.dateAdded)
    .sort((a, b) => (b.dateAdded! > a.dateAdded! ? 1 : -1))
    .slice(0, SHELF_CAP),
)

const collectionGroups = computed(() => {
  const map = new Map<string, Game[]>()
  for (const g of games.value) {
    for (const c of g.collections) {
      if (!map.has(c)) map.set(c, [])
      map.get(c)!.push(g)
    }
  }
  return Array.from(map.entries()).map(([name, list]) => ({ name, games: list.slice(0, SHELF_CAP) }))
})

const collectionsCount = computed(() => collectionGroups.value.length)

function scrollShelf(e: MouseEvent, dir: 1 | -1) {
  const row = (e.currentTarget as HTMLElement).closest('.row')
  const shelf = row?.querySelector('.shelf') as HTMLElement | null
  if (!shelf) return
  shelf.scrollBy({ left: dir * shelf.clientWidth * 0.9, behavior: 'smooth' })
}
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

    <div v-if="currentUser" class="profile-chip">
      <span class="profile-name">{{ currentUser.username }}</span>
      <div class="profile-avatar">{{ currentUser.username.slice(0, 2).toUpperCase() }}</div>
    </div>

    <div class="content">
      <div class="home-header">
        <p class="eyebrow">Welcome back, {{ currentUser?.username }}</p>
        <h1>Your Library</h1>
      </div>

      <div class="stats-strip">
        <div class="stat-card">
          <span class="stat-value">{{ totalGames }}</span>
          <span class="stat-label">Games</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ favoriteCount }}</span>
          <span class="stat-label">Favorites</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ collectionsCount }}</span>
          <span class="stat-label">Collections</span>
        </div>
      </div>

      <section class="widgets-row">
        <button type="button" class="widget-card random-widget" @click="pickRandomGame">
          <svg class="widget-icon" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="4" />
            <circle cx="8.5" cy="8.5" r="1.2" fill="currentColor" stroke="none" />
            <circle cx="15.5" cy="8.5" r="1.2" fill="currentColor" stroke="none" />
            <circle cx="8.5" cy="15.5" r="1.2" fill="currentColor" stroke="none" />
            <circle cx="15.5" cy="15.5" r="1.2" fill="currentColor" stroke="none" />
            <circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none" />
          </svg>
          <div>
            <span class="widget-title">Pick something random</span>
            <span class="widget-subtitle">Can't decide? Let us choose.</span>
          </div>
        </button>

        <div class="widget-card goals-widget disabled">
          <svg class="widget-icon" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9" />
            <circle cx="12" cy="12" r="5" />
            <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
          </svg>
          <div>
            <span class="widget-title">Goals & bounties</span>
            <span class="widget-subtitle">Coming soon</span>
          </div>
        </div>
      </section>

      <p v-if="loading">Loading…</p>
      <p v-else-if="error" class="error">{{ error }}</p>

      <template v-else>
        <section class="row">
          <div class="row-header">
            <router-link to="/games?status=playing" class="row-title">
              <svg class="row-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="2" y="6" width="20" height="12" rx="6" />
                <line x1="7" y1="12" x2="11" y2="12" />
                <line x1="9" y1="10" x2="9" y2="14" />
                <circle cx="16" cy="10.5" r="1" fill="currentColor" stroke="none" />
                <circle cx="18" cy="13" r="1" fill="currentColor" stroke="none" />
              </svg>
              <h2>Continue Playing</h2>
              <span class="row-count">{{ playingGames.length }}</span>
            </router-link>
          </div>
          <div v-if="playingGames.length" class="shelf-wrap">
            <button type="button" class="shelf-arrow left" @click="scrollShelf($event, -1)" aria-label="Scroll left">‹</button>
            <div class="shelf" @scroll="updateShelfArrows($event.target as HTMLElement)">
              <GameCard
                v-for="game in playingGames"
                :key="game.id"
                :game="game"
                @hover="setHoverImage"
                @edit="openEditModal"
                @add-to-collection="handleAddToCollection"
              />
            </div>
            <button type="button" class="shelf-arrow right" @click="scrollShelf($event, 1)" aria-label="Scroll right">›</button>
          </div>
          <p v-else class="empty-row">Nothing in progress right now.</p>
        </section>

        <section class="row">
          <div class="row-header">
            <router-link to="/games?sort=recent" class="row-title">
              <svg class="row-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="9" />
                <polyline points="12 7 12 12 15.5 14" />
              </svg>
              <h2>Recently Added</h2>
              <span class="row-count">{{ recentlyAdded.length }}</span>
            </router-link>
          </div>
          <div v-if="recentlyAdded.length" class="shelf-wrap">
            <button type="button" class="shelf-arrow left" @click="scrollShelf($event, -1)" aria-label="Scroll left">‹</button>
            <div class="shelf" @scroll="updateShelfArrows($event.target as HTMLElement)">
              <GameCard
                v-for="game in recentlyAdded"
                :key="game.id"
                :game="game"
                @hover="setHoverImage"
                @edit="openEditModal"
                @add-to-collection="handleAddToCollection"
              />
            </div>
            <button type="button" class="shelf-arrow right" @click="scrollShelf($event, 1)" aria-label="Scroll right">›</button>
          </div>
          <p v-else class="empty-row">No games added yet.</p>
        </section>

        <section v-for="group in collectionGroups" :key="group.name" class="row">
          <div class="row-header">
            <router-link :to="`/collections/${encodeURIComponent(group.name)}`" class="row-title">
              <svg class="row-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              </svg>
              <h2>{{ group.name }}</h2>
              <span class="row-count">{{ group.games.length }}</span>
            </router-link>
          </div>
          <div class="shelf-wrap">
            <button type="button" class="shelf-arrow left" @click="scrollShelf($event, -1)" aria-label="Scroll left">‹</button>
            <div class="shelf" @scroll="updateShelfArrows($event.target as HTMLElement)">
              <GameCard
                v-for="game in group.games"
                :key="game.id"
                :game="game"
                @hover="setHoverImage"
                @edit="openEditModal"
                @add-to-collection="handleAddToCollection"
              />
            </div>
            <button type="button" class="shelf-arrow right" @click="scrollShelf($event, 1)" aria-label="Scroll right">›</button>
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
        @delete="onDeleteFromModal"
      />

      <CollectionPickerModal
        v-if="collectionPickerGame"
        :game="collectionPickerGame"
        @close="collectionPickerGame = null"
        @added="onCollectionAdded"
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
.home::before {
  content: '';
  position: fixed;
  top: -100px;
  left: -100px;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(214, 138, 52, 0.08) 0%, transparent 70%);
  z-index: 0;
  pointer-events: none;
}
.ambient-bg {
  position: fixed;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: blur(90px);
  opacity: 0;
  transform: scale(1.2);
  transition: opacity 1.4s cubic-bezier(0.22, 1, 0.36, 1);
  z-index: 0;
}
.ambient-bg.visible {
  opacity: 0.35;
}
.content {
  position: relative;
  z-index: 1;
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
.home-header {
  margin-bottom: 28px;
}
.eyebrow {
  margin: 0 0 4px;
  color: #d68a34;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.home-header h1 {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 700;
  color: #fff;
}
.stats-strip {
  display: flex;
  gap: 14px;
  margin-bottom: 24px;
}
.stat-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #232323;
  border-radius: 10px;
  padding: 10px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 80px;
  transition: transform 0.15s ease, border-color 0.15s ease;
}
.stat-card:hover {
  transform: translateY(-2px);
  border-color: #3a3a3a;
}
.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #d68a34;
}
.stat-label {
  font-size: 12px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.widgets-row {
  display: flex;
  gap: 14px;
  margin-bottom: 32px;
}
.widget-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #232323;
  border-radius: 12px;
  padding: 14px 18px;
  flex: 1;
  max-width: 280px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}
.random-widget:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: #3a3a3a;
  transform: translateY(-2px);
}
.widget-card.disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.widget-icon {
  color: #d68a34;
  flex-shrink: 0;
}
.widget-title {
  display: block;
  color: #fff;
  font-weight: 600;
  font-size: 14px;
}
.widget-subtitle {
  display: block;
  color: #888;
  font-size: 12px;
  margin-top: 2px;
}
.row {
  margin-bottom: 32px;
}
.row-header {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
}
.row-title {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 12px;
  border-left: 3px solid #d68a34;
  text-decoration: none;
  cursor: pointer;
}
.row-title:hover h2 {
  color: #d68a34;
}
.row-title h2 {
  margin: 0;
  font-size: 1.1rem;
  color: #fff;
  transition: color 0.15s ease;
}
.row-icon {
  color: #d68a34;
  flex-shrink: 0;
}
.row-count {
  background: rgba(255, 255, 255, 0.06);
  color: #999;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 999px;
}
.shelf-wrap {
  position: relative;
}
.shelf {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  scroll-behavior: smooth;
  padding: 20px 16px 28px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.shelf::-webkit-scrollbar {
  display: none;
}
.shelf-arrow {
  position: absolute;
  top: 0;
  bottom: 28px;
  width: 40px;
  border: none;
  background: linear-gradient(to right, rgba(10, 10, 10, 0.85), transparent);
  color: #fff;
  font-size: 26px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
}
.shelf-arrow.right {
  left: auto;
  right: 0;
  background: linear-gradient(to left, rgba(10, 10, 10, 0.85), transparent);
}
.shelf-arrow.left {
  left: 0;
}
.shelf-wrap:hover .shelf-arrow.can-scroll {
  opacity: 1;
  pointer-events: auto;
}
.shelf-arrow:hover {
  color: #d68a34;
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