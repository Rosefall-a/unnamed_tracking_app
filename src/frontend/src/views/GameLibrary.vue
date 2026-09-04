<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GameCard from '../components/GameCard.vue'
import GameFormModal from '../components/GameFormModal.vue'
import FilterCombobox from '../components/FilterCombobox.vue'
import { fetchGames, deleteGame, setFavorite } from '../services/games'
import CollectionPickerModal from '../components/CollectionPickerModal.vue'
import { computeScore } from '../utils/scoring'
import DOMPurify from 'dompurify'
import { normalizePlatformFamily, PLATFORM_OPTIONS, RETRO_PLATFORM_OPTIONS } from '../utils/platforms'
import { GENRE_OPTIONS } from '../utils/genres'
import type { Game, GameStatus } from '../types/game'
import { currentUser } from '../state/auth'

type ViewMode = 'cards' | 'list' | 'detail'
type SortBy = 'name' | 'recent' | 'rating' | 'playtime'
type AchievementsFilter = 'all' | 'has' | 'none'

const router = useRouter()
const route = useRoute()

const games = ref<Game[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const showFormModal = ref(false)
const editingGame = ref<Game | null>(null)

const deletingGame = ref<Game | null>(null)
const deleting = ref(false)
const deleteError = ref<string | null>(null)

const viewMode = ref<ViewMode>((localStorage.getItem('gameLibraryViewMode') as ViewMode) || 'cards')
const selectedGame = ref<Game | null>(null)

// Steam's "About This Game" section is rich HTML (headers, screenshots,
// gifs) — sanitize it instead of dumping the raw tags as text
const selectedGameDescriptionHtml = computed(() => {
  if (!selectedGame.value?.description) return ''
  return DOMPurify.sanitize(selectedGame.value.description)
})

// filters persist across visits (localStorage) so they don't silently reset
// every time you navigate away and back
const FILTERS_KEY = 'gameLibraryFilters'
interface PersistedFilters {
  searchQuery: string
  statusFilter: GameStatus | 'all'
  platformFilter: string
  genreFilter: string
  sortBy: SortBy
  showAdvancedFilters: boolean
  franchiseFilter: string
  collectionFilter: string
  companyFilter: string
  ageRatingFilter: string
  regionFilter: string
  languageFilter: string
  metadataProviderFilter: string
  favoritesOnly: boolean
  achievementsFilter: AchievementsFilter
  retroAchievementsOnly: boolean
}
function loadPersistedFilters(): Partial<PersistedFilters> {
  try {
    const raw = localStorage.getItem(FILTERS_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}
const persisted = loadPersistedFilters()

const searchQuery = ref(persisted.searchQuery ?? '')
const statusFilter = ref<GameStatus | 'all'>(persisted.statusFilter ?? 'all')
const platformFilter = ref<string>(persisted.platformFilter ?? 'all')
const genreFilter = ref<string>(persisted.genreFilter ?? 'all')
const sortBy = ref<SortBy>(
  persisted.sortBy ?? (localStorage.getItem('gameLibraryDefaultSort') as SortBy) ?? 'name',
)

const showAdvancedFilters = ref(persisted.showAdvancedFilters ?? false)
const franchiseFilter = ref<string>(persisted.franchiseFilter ?? 'all')
const collectionFilter = ref<string>(persisted.collectionFilter ?? 'all')
const companyFilter = ref<string>(persisted.companyFilter ?? 'all')
const ageRatingFilter = ref<string>(persisted.ageRatingFilter ?? 'all')
const regionFilter = ref<string>(persisted.regionFilter ?? 'all')
const languageFilter = ref<string>(persisted.languageFilter ?? 'all')
const metadataProviderFilter = ref<string>(persisted.metadataProviderFilter ?? 'all')
const favoritesOnly = ref(persisted.favoritesOnly ?? false)
const achievementsFilter = ref<AchievementsFilter>(persisted.achievementsFilter ?? 'all')
const retroAchievementsOnly = ref(persisted.retroAchievementsOnly ?? false)

watch(
  [
    searchQuery, statusFilter, platformFilter, genreFilter, sortBy, showAdvancedFilters,
    franchiseFilter, collectionFilter, companyFilter, ageRatingFilter, regionFilter,
    languageFilter, metadataProviderFilter, favoritesOnly, achievementsFilter, retroAchievementsOnly,
  ],
  () => {
    const toSave: PersistedFilters = {
      searchQuery: searchQuery.value,
      statusFilter: statusFilter.value,
      platformFilter: platformFilter.value,
      genreFilter: genreFilter.value,
      sortBy: sortBy.value,
      showAdvancedFilters: showAdvancedFilters.value,
      franchiseFilter: franchiseFilter.value,
      collectionFilter: collectionFilter.value,
      companyFilter: companyFilter.value,
      ageRatingFilter: ageRatingFilter.value,
      regionFilter: regionFilter.value,
      languageFilter: languageFilter.value,
      metadataProviderFilter: metadataProviderFilter.value,
      favoritesOnly: favoritesOnly.value,
      achievementsFilter: achievementsFilter.value,
      retroAchievementsOnly: retroAchievementsOnly.value,
    }
    localStorage.setItem(FILTERS_KEY, JSON.stringify(toSave))
  },
)

const advancedFilterCount = computed(() => {
  let count = 0
  if (franchiseFilter.value !== 'all') count++
  if (collectionFilter.value !== 'all') count++
  if (companyFilter.value !== 'all') count++
  if (ageRatingFilter.value !== 'all') count++
  if (regionFilter.value !== 'all') count++
  if (languageFilter.value !== 'all') count++
  if (metadataProviderFilter.value !== 'all') count++
  if (favoritesOnly.value) count++
  if (achievementsFilter.value !== 'all') count++
  if (retroAchievementsOnly.value) count++
  return count
})

function clearAdvancedFilters() {
  franchiseFilter.value = 'all'
  collectionFilter.value = 'all'
  companyFilter.value = 'all'
  ageRatingFilter.value = 'all'
  regionFilter.value = 'all'
  languageFilter.value = 'all'
  metadataProviderFilter.value = 'all'
  favoritesOnly.value = false
  achievementsFilter.value = 'all'
  retroAchievementsOnly.value = false
}

// arriving from a Collections-page card click (?collection=Name) —
// pre-apply that filter and surface the panel so it's clear why it's active
const queryCollection = route.query.collection
if (typeof queryCollection === 'string' && queryCollection) {
  collectionFilter.value = queryCollection
  showAdvancedFilters.value = true
}

const statusOptions: (GameStatus | 'all')[] = [
  'all',
  'wishlist',
  'backlog',
  'playing',
  'on hold',
  'beaten',
  'played',
  'dropped',
  'mastered',
]

// arriving from a Home Hub row link (?status=playing, ?sort=recent)
const queryStatus = route.query.status
if (typeof queryStatus === 'string' && statusOptions.includes(queryStatus as GameStatus | 'all')) {
  statusFilter.value = queryStatus as GameStatus | 'all'
}
const querySort = route.query.sort
if (typeof querySort === 'string' && ['name', 'recent', 'rating', 'playtime'].includes(querySort)) {
  sortBy.value = querySort as SortBy
}

const platformOptions = computed(() => {
  const set = new Set<string>(PLATFORM_OPTIONS)
  games.value.forEach((g) =>
    g.platforms.forEach((p) => {
      const family = normalizePlatformFamily(p.platform)
      if (PLATFORM_OPTIONS.includes(family)) set.add(family)
    }),
  )
  return Array.from(set).sort()
})

const platformExtraOptions = computed(() => {
  const set = new Set<string>(RETRO_PLATFORM_OPTIONS)
  games.value.forEach((g) =>
    g.platforms.forEach((p) => {
      const family = normalizePlatformFamily(p.platform)
      if (!PLATFORM_OPTIONS.includes(family)) set.add(family)
    }),
  )
  return Array.from(set).sort()
})

const genreOptions = computed(() => {
  const set = new Set<string>(GENRE_OPTIONS)
  games.value.forEach((g) => g.tags.forEach((t) => set.add(t)))
  return Array.from(set).sort()
})

function uniqueValues(pick: (g: Game) => string | null): string[] {
  const set = new Set<string>()
  games.value.forEach((g) => {
    const value = pick(g)
    if (value) set.add(value)
  })
  return Array.from(set).sort()
}

const franchiseOptions = computed(() => uniqueValues((g) => g.series))
const collectionOptions = computed(() => {
  const set = new Set<string>()
  games.value.forEach((g) => g.collections.forEach((c) => set.add(c)))
  return Array.from(set).sort()
})
const companyOptions = computed(() => {
  const set = new Set<string>()
  games.value.forEach((g) => {
    if (g.developer) set.add(g.developer)
    if (g.publisher) set.add(g.publisher)
  })
  return Array.from(set).sort()
})
const ageRatingOptions = computed(() => uniqueValues((g) => g.ageRating))
const regionOptions = computed(() => uniqueValues((g) => g.region))
const languageOptions = computed(() => uniqueValues((g) => g.language))
const metadataProviderOptions = computed(() => uniqueValues((g) => g.source))

function setView(mode: ViewMode) {
  viewMode.value = mode
  localStorage.setItem('gameLibraryViewMode', mode)
  if (mode === 'detail' && !selectedGame.value && games.value.length) {
    selectedGame.value = games.value[0]
  }
}

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

async function loadGames() {
  loading.value = true
  try {
    games.value = await fetchGames()
    if (viewMode.value === 'detail' && !selectedGame.value && games.value.length) {
      selectedGame.value = games.value[0]
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load games'
  } finally {
    loading.value = false
  }
}

onMounted(loadGames)

// filters are only remembered while you stay on this page — leaving it
// (any other route) wipes them so the next visit starts from a clean slate
onUnmounted(() => {
  localStorage.removeItem(FILTERS_KEY)
})

function openAddModal() {
  editingGame.value = null
  showFormModal.value = true
}

function openEditModal(game: Game) {
  editingGame.value = game
  showFormModal.value = true
}

async function onGameSaved() {
  showFormModal.value = false
  editingGame.value = null
  await loadGames()
}

function onDeleteFromModal(gameId: string) {
  const game = games.value.find((g) => g.id === gameId)
  showFormModal.value = false
  editingGame.value = null
  if (game) requestDelete(game)
}

function requestDelete(game: Game) {
  deletingGame.value = game
  deleteError.value = null
}

async function toggleFavorite(game: Game) {
  const next = !game.favorite
  game.favorite = next
  try {
    await setFavorite(game.id, next)
  } catch {
    game.favorite = !next
  }
}

const collectionPickerGame = ref<Game | null>(null)

function handleAddToCollection(game: Game) {
  collectionPickerGame.value = game
}

async function onCollectionAdded() {
  await loadGames()
}

async function confirmDelete() {
  if (!deletingGame.value) return
  deleting.value = true
  deleteError.value = null
  try {
    await deleteGame(deletingGame.value.id)
    if (selectedGame.value?.id === deletingGame.value.id) selectedGame.value = null
    deletingGame.value = null
    await loadGames()
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : 'Failed to delete game'
  } finally {
    deleting.value = false
  }
}

function gameTotalMinutes(game: Game): number {
  return game.platforms.reduce((sum, p) => sum + p.playtimeMinutes, 0)
}

function totalPlaytime(game: Game): string {
  const minutes = gameTotalMinutes(game)
  if (minutes === 0) return '—'
  const hours = Math.floor(minutes / 60)
  return `${hours}h`
}

function gameLastPlayed(game: Game): string | null {
  const dates = game.platforms.map((p) => p.lastPlayedAt).filter((d): d is string => d !== null)
  return dates.length ? dates.reduce((latest, d) => (d > latest ? d : latest)) : null
}

function openGame(game: Game) {
  router.push(`/games/${game.id}`)
}

const filteredGames = computed(() => {
  let result = games.value

  if (statusFilter.value !== 'all') {
    result = result.filter((g) => g.status === statusFilter.value)
  }
  if (platformFilter.value !== 'all') {
    result = result.filter((g) => g.platforms.some((p) => normalizePlatformFamily(p.platform) === platformFilter.value))
  }
  if (genreFilter.value !== 'all') {
    result = result.filter((g) => g.tags.includes(genreFilter.value))
  }
  if (franchiseFilter.value !== 'all') {
    result = result.filter((g) => g.series === franchiseFilter.value)
  }
  if (collectionFilter.value !== 'all') {
    result = result.filter((g) => g.collections.includes(collectionFilter.value))
  }
  if (companyFilter.value !== 'all') {
    result = result.filter((g) => g.developer === companyFilter.value || g.publisher === companyFilter.value)
  }
  if (ageRatingFilter.value !== 'all') {
    result = result.filter((g) => g.ageRating === ageRatingFilter.value)
  }
  if (regionFilter.value !== 'all') {
    result = result.filter((g) => g.region === regionFilter.value)
  }
  if (languageFilter.value !== 'all') {
    result = result.filter((g) => g.language === languageFilter.value)
  }
  if (metadataProviderFilter.value !== 'all') {
    result = result.filter((g) => g.source === metadataProviderFilter.value)
  }
  if (favoritesOnly.value) {
    result = result.filter((g) => g.favorite)
  }
  if (achievementsFilter.value === 'has') {
    result = result.filter((g) => g.achievements.length > 0)
  } else if (achievementsFilter.value === 'none') {
    result = result.filter((g) => g.achievements.length === 0)
  }
  if (retroAchievementsOnly.value) {
    result = result.filter((g) => g.achievementsProvider === 'retroachievements')
  }

  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    result = result.filter((g) => g.title.toLowerCase().includes(q))
  }

  result = [...result].sort((a, b) => {
    if (sortBy.value === 'name') return a.title.localeCompare(b.title)
    if (sortBy.value === 'recent') return (b.dateAdded ?? '').localeCompare(a.dateAdded ?? '')
    if (sortBy.value === 'rating') {
      const scoreA = computeScore(a)?.sum ?? -1
      const scoreB = computeScore(b)?.sum ?? -1
      return scoreB - scoreA
    }
    if (sortBy.value === 'playtime') return gameTotalMinutes(b) - gameTotalMinutes(a)
    return 0
  })

  return result
})
</script>

<template>
  <main class="library" :class="{ locked: viewMode === 'detail' }">
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
      <div class="header-row">
        <h1>Games</h1>
        <div class="header-actions">
          <input v-model="searchQuery" type="text" class="search-input" placeholder="Search games…" />
          <select v-model="statusFilter" class="filter-select">
            <option v-for="s in statusOptions" :key="s" :value="s">
              {{ s === 'all' ? 'All statuses' : s }}
            </option>
          </select>
          <FilterCombobox
            v-model="platformFilter"
            :options="platformOptions"
            :extra-options="platformExtraOptions"
            extra-label="Retro"
            placeholder="Platform"
            all-label="All platforms"
          />
          <FilterCombobox v-model="genreFilter" :options="genreOptions" placeholder="Genre" all-label="All genres" />
          <select v-model="sortBy" class="filter-select">
            <option value="name">Name</option>
            <option value="recent">Recently added</option>
            <option value="rating">Rating</option>
            <option value="playtime">Most Played</option>
          </select>

          <div class="view-toggle">
            <button
              type="button"
              class="view-toggle-button"
              :class="{ active: viewMode === 'cards' }"
              title="Cards"
              @click="setView('cards')"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="8" height="8" rx="1" />
                <rect x="13" y="3" width="8" height="8" rx="1" />
                <rect x="3" y="13" width="8" height="8" rx="1" />
                <rect x="13" y="13" width="8" height="8" rx="1" />
              </svg>
            </button>
            <button
              type="button"
              class="view-toggle-button"
              :class="{ active: viewMode === 'list' }"
              title="List"
              @click="setView('list')"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="4" y1="6" x2="20" y2="6" />
                <line x1="4" y1="12" x2="20" y2="12" />
                <line x1="4" y1="18" x2="20" y2="18" />
              </svg>
            </button>
            <button
              type="button"
              class="view-toggle-button"
              :class="{ active: viewMode === 'detail' }"
              title="List + preview"
              @click="setView('detail')"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="7" height="18" rx="1" />
                <rect x="13" y="3" width="8" height="18" rx="1" />
              </svg>
            </button>
          </div>

          <button
            type="button"
            class="advanced-toggle"
            :class="{ active: showAdvancedFilters }"
            @click="showAdvancedFilters = !showAdvancedFilters"
          >
            Advanced Filters
            <span v-if="advancedFilterCount" class="advanced-count">{{ advancedFilterCount }}</span>
          </button>

          <button type="button" class="add-button" @click="openAddModal">+ Add Game</button>
        </div>
      </div>

      <div v-if="showAdvancedFilters" class="advanced-panel">
        <div class="advanced-field">
          <label>Franchise</label>
          <FilterCombobox v-model="franchiseFilter" :options="franchiseOptions" placeholder="Franchise" all-label="All franchises" />
        </div>
        <div class="advanced-field">
          <label>Collection</label>
          <FilterCombobox v-model="collectionFilter" :options="collectionOptions" placeholder="Collection" all-label="All collections" />
        </div>
        <div class="advanced-field">
          <label>Company</label>
          <FilterCombobox v-model="companyFilter" :options="companyOptions" placeholder="Company" all-label="All companies" />
        </div>
        <div class="advanced-field">
          <label>Age Rating</label>
          <FilterCombobox v-model="ageRatingFilter" :options="ageRatingOptions" placeholder="Age rating" all-label="All ratings" />
        </div>
        <div class="advanced-field">
          <label>Region</label>
          <FilterCombobox v-model="regionFilter" :options="regionOptions" placeholder="Region" all-label="All regions" />
        </div>
        <div class="advanced-field">
          <label>Language</label>
          <FilterCombobox v-model="languageFilter" :options="languageOptions" placeholder="Language" all-label="All languages" />
        </div>
        <div class="advanced-field">
          <label>Metadata Provider</label>
          <FilterCombobox v-model="metadataProviderFilter" :options="metadataProviderOptions" placeholder="Provider" all-label="All providers" />
        </div>
        <div class="advanced-field">
          <label>Achievements</label>
          <select v-model="achievementsFilter" class="filter-select">
            <option value="all">All games</option>
            <option value="has">Has achievements</option>
            <option value="none">No achievements</option>
          </select>
        </div>
        <div class="advanced-toggles">
          <button
            type="button"
            class="toggle-chip"
            :class="{ active: favoritesOnly }"
            @click="favoritesOnly = !favoritesOnly"
          >
            ★ Favorites only
          </button>
          <button
            type="button"
            class="toggle-chip"
            :class="{ active: retroAchievementsOnly }"
            @click="retroAchievementsOnly = !retroAchievementsOnly"
          >
            Has RetroAchievements tracking
          </button>
          <button type="button" class="clear-advanced" :disabled="!advancedFilterCount" @click="clearAdvancedFilters">
            Clear advanced filters
          </button>
        </div>
      </div>

      <p v-if="loading">Loading…</p>
      <p v-else-if="error" class="error">{{ error }}</p>

      <template v-else>
        <div v-if="viewMode === 'cards'" class="grid">
          <GameCard
            v-for="game in filteredGames"
            :key="game.id"
            :game="game"
            @hover="setHoverImage"
            @edit="openEditModal"
            @add-to-collection="handleAddToCollection"
          />
        </div>

        <div v-else-if="viewMode === 'list'" class="list-view">
          <div v-if="filteredGames.length" class="list-header">
            <span class="list-header-spacer"></span>
            <span class="list-title">Name</span>
            <span class="list-status">Status</span>
            <span class="list-genre">Genre</span>
            <span class="list-platform">Platform</span>
            <span class="list-score">Rating</span>
            <span class="list-playtime">Playtime</span>
            <span class="list-last-played">Last played</span>
            <span class="list-release">Released</span>
            <span class="list-actions-spacer"></span>
          </div>
          <div v-for="game in filteredGames" :key="game.id" class="list-row" @click="openGame(game)">
            <img class="list-cover" :src="game.coverImageUrl" alt="" />
            <span class="list-title">{{ game.title }}</span>
            <span class="list-status"><span class="status-pill">{{ game.status }}</span></span>
            <span class="list-genre">{{ game.tags[0] ?? '—' }}</span>
            <span class="list-platform">{{ game.platforms[0]?.platform ?? '—' }}</span>
            <span class="list-score">
              <template v-if="computeScore(game)">★ {{ computeScore(game)!.sum.toFixed(1) }}</template>
              <template v-else>—</template>
            </span>
            <span class="list-playtime">{{ totalPlaytime(game) }}</span>
            <span class="list-last-played">
              {{ gameLastPlayed(game) ? new Date(gameLastPlayed(game)!).toLocaleDateString() : '—' }}
            </span>
            <span class="list-release">
              {{ game.releaseDate ? new Date(game.releaseDate).toLocaleDateString() : '—' }}
            </span>
            <div class="list-actions">
              <button type="button" class="small-button" @click.stop="openEditModal(game)">Edit</button>
              <button
                type="button"
                class="icon-button"
                title="Add to collection"
                @click.stop="handleAddToCollection(game)"
              >
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                </svg>
              </button>
              <button
                type="button"
                class="icon-button"
                :class="{ active: game.favorite }"
                :title="game.favorite ? 'Remove from favorites' : 'Add to favorites'"
                @click.stop="toggleFavorite(game)"
              >
                <svg viewBox="0 0 24 24" width="16" height="16" :fill="game.favorite ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.6z" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div v-else class="detail-view">
          <div class="detail-list">
            <button
              v-for="game in filteredGames"
              :key="game.id"
              type="button"
              class="detail-list-item"
              :class="{ active: selectedGame?.id === game.id }"
              @click="selectedGame = game"
            >
              <img class="detail-list-thumb" :src="game.coverImageUrl" alt="" />
              <span>{{ game.title }}</span>
            </button>
          </div>

          <Transition name="preview-fade" mode="out-in">
            <div v-if="selectedGame" :key="selectedGame.id" class="detail-preview">
              <div class="preview-banner" :style="{ backgroundImage: `url(${selectedGame.bannerImageUrl})` }">
                <div class="preview-banner-overlay"></div>
              </div>
              <div class="preview-info">
                <h2>{{ selectedGame.title }}</h2>
                <div class="preview-meta">
                  <span class="preview-badge">{{ selectedGame.status }}</span>
                  <span v-if="computeScore(selectedGame)" class="preview-badge score">
                    ★ {{ computeScore(selectedGame)!.sum.toFixed(1) }}
                  </span>
                  <span class="preview-badge">{{ totalPlaytime(selectedGame) }}</span>
                </div>
                <div class="preview-details">
                  <div v-if="selectedGame.developer" class="preview-detail-row">
                    <span class="preview-detail-label">Developer</span>
                    <span>{{ selectedGame.developer }}</span>
                  </div>
                  <div v-if="selectedGame.publisher" class="preview-detail-row">
                    <span class="preview-detail-label">Publisher</span>
                    <span>{{ selectedGame.publisher }}</span>
                  </div>
                  <div v-if="selectedGame.series" class="preview-detail-row">
                    <span class="preview-detail-label">Series</span>
                    <span>{{ selectedGame.series }}</span>
                  </div>
                  <div v-if="selectedGame.source" class="preview-detail-row">
                    <span class="preview-detail-label">Source</span>
                    <span>{{ selectedGame.source }}</span>
                  </div>
                  <div v-if="selectedGame.ageRating" class="preview-detail-row">
                    <span class="preview-detail-label">Age Rating</span>
                    <span>{{ selectedGame.ageRating }}</span>
                  </div>
                  <div v-if="selectedGame.releaseDate" class="preview-detail-row">
                    <span class="preview-detail-label">Released</span>
                    <span>{{ new Date(selectedGame.releaseDate).toLocaleDateString() }}</span>
                  </div>
                  <div v-if="selectedGame.dateAdded" class="preview-detail-row">
                    <span class="preview-detail-label">Added</span>
                    <span>{{ new Date(selectedGame.dateAdded).toLocaleDateString() }}</span>
                  </div>
                  <div v-if="selectedGame.platforms.length" class="preview-detail-row">
                    <span class="preview-detail-label">Platforms</span>
                    <div class="preview-platforms">
                      <div v-for="p in selectedGame.platforms" :key="p.platform">
                        {{ p.platform }} — {{ Math.round(p.playtimeMinutes / 60) }}h
                        <span v-if="p.completionPercent !== null">· {{ p.completionPercent }}%</span>
                      </div>
                    </div>
                  </div>
                  <div v-if="selectedGame.tags.length" class="preview-detail-row">
                    <span class="preview-detail-label">Tags</span>
                    <span class="preview-pills">
                      <span v-for="tag in selectedGame.tags" :key="tag" class="preview-pill">{{ tag }}</span>
                    </span>
                  </div>
                  <div v-if="selectedGame.features.length" class="preview-detail-row">
                    <span class="preview-detail-label">Features</span>
                    <span class="preview-pills">
                      <span v-for="f in selectedGame.features" :key="f" class="preview-pill">{{ f }}</span>
                    </span>
                  </div>
                  <div v-if="selectedGame.links.length" class="preview-detail-row">
                    <span class="preview-detail-label">Links</span>
                    <div class="preview-links">
                      <a
                        v-for="link in selectedGame.links"
                        :key="link.url"
                        :href="link.url"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {{ link.label }}
                      </a>
                    </div>
                  </div>
                  <div
                    v-if="selectedGame.ownership.format || selectedGame.ownership.price !== null"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Ownership</span>
                    <span>
                      {{ selectedGame.ownership.format ?? '—' }}
                      <span v-if="selectedGame.ownership.price !== null">
                        · {{ selectedGame.ownership.priceCurrency ?? 'USD' }} {{ selectedGame.ownership.price.toFixed(2) }}
                      </span>
                    </span>
                  </div>
                  <div v-if="selectedGame.folderLocation" class="preview-detail-row">
                    <span class="preview-detail-label">Folder</span>
                    <span>{{ selectedGame.folderLocation }}</span>
                  </div>
                </div>
                <div v-if="selectedGameDescriptionHtml" class="preview-description-html" v-html="selectedGameDescriptionHtml"></div>
                <div class="preview-actions">
                  <button type="button" class="primary-button" @click="openGame(selectedGame)">
                    Open Full Page
                  </button>
                  <button type="button" class="secondary-button" @click="openEditModal(selectedGame)">Edit</button>
                  <button
                    type="button"
                    class="icon-button"
                    title="Add to collection"
                    @click="handleAddToCollection(selectedGame)"
                  >
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="icon-button"
                    :class="{ active: selectedGame.favorite }"
                    :title="selectedGame.favorite ? 'Remove from favorites' : 'Add to favorites'"
                    @click="toggleFavorite(selectedGame)"
                  >
                    <svg viewBox="0 0 24 24" width="16" height="16" :fill="selectedGame.favorite ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.6z" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </Transition>
          <p v-if="!selectedGame" class="empty-row">Select a game to preview it.</p>
        </div>
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
.library {
  position: relative;
  padding: 84px 24px 24px;
  font-family: system-ui, sans-serif;
  background: #121212;
  min-height: 100vh;
  color: #fff;
  overflow-x: hidden;
}
/* List + preview mode: the page itself doesn't scroll — only the list and
   preview panes do, via their own overflow-y (see .detail-list/.detail-preview) */
.library.locked {
  height: 100vh;
  overflow-y: hidden;
  box-sizing: border-box;
}
/* let the panels stretch to fill whatever room is actually left below the
   header/filters, instead of guessing that height with a fixed calc() */
.library.locked .content {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.library.locked .detail-view {
  flex: 1;
  height: auto;
  min-height: 0;
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
  width: 200px;
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
.view-toggle {
  display: flex;
  gap: 2px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 3px;
  height: 40px;
  box-sizing: border-box;
}
.view-toggle-button {
  background: none;
  border: none;
  color: #999;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease, color 0.15s ease;
}
.view-toggle-button:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
}
.view-toggle-button.active {
  color: #111;
  background: #d68a34;
  box-shadow: 0 2px 8px rgba(214, 138, 52, 0.4);
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
   on how many games there are, so adding one more game just starts filling
   the next row instead of resizing every existing card */
.grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 16px;
}
.grid :deep(.game-card-wrap) {
  width: auto;
  min-width: 0;
}

/* Advanced filters */
.advanced-toggle {
  height: 40px;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #ccc;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.advanced-toggle:hover {
  color: #fff;
  border-color: #4a4a4a;
}
.advanced-toggle.active {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.5);
  background: rgba(214, 138, 52, 0.1);
}
.advanced-count {
  background: #d68a34;
  color: #111;
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  min-width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
}
.advanced-panel {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #232323;
  border-radius: 10px;
  padding: 18px 20px;
  margin-bottom: 24px;
}
.advanced-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.advanced-field label {
  color: #888;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}
.advanced-field .combobox,
.advanced-field .filter-select {
  width: 100%;
}
.advanced-toggles {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding-top: 6px;
  border-top: 1px solid #232323;
  margin-top: 4px;
}
.toggle-chip {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid #3a3a3a;
  color: #ccc;
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.toggle-chip:hover {
  border-color: #4a4a4a;
}
.toggle-chip.active {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.5);
  background: rgba(214, 138, 52, 0.14);
}
.clear-advanced {
  margin-left: auto;
  background: none;
  border: none;
  color: #999;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}
.clear-advanced:hover:not(:disabled) {
  color: #fff;
}
.clear-advanced:disabled {
  color: #555;
  cursor: not-allowed;
  text-decoration: none;
}

.error {
  color: #f87171;
}

/* List view */
.list-view {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.list-header {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 28px 8px;
}
.list-header span {
  color: #666;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}
.list-header-spacer {
  width: 44px;
  flex-shrink: 0;
}
.list-actions-spacer {
  width: 130px;
  flex-shrink: 0;
}
.list-row {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 28px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #232323;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.list-row:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: #333;
  transform: translateX(2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
.list-cover {
  width: 44px;
  height: 58px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}
.list-title {
  flex: 1;
  font-weight: 600;
  font-size: 14.5px;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.list-status {
  width: 100px;
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  text-transform: capitalize;
  color: #ccc;
  font-size: 12px;
}
.status-pill {
  width: 82px;
  text-align: center;
  background: rgba(255, 255, 255, 0.06);
  padding: 4px 0;
  border-radius: 999px;
}
.list-header .list-status {
  text-align: center;
}
.list-genre,
.list-platform,
.list-last-played,
.list-release {
  color: #999;
  font-size: 12px;
  min-width: 100px;
}
.list-score {
  min-width: 60px;
  color: #d68a34;
  font-size: 12px;
  font-weight: 700;
}
.list-header .list-score {
  color: #666;
  font-weight: 600;
}
.list-playtime {
  width: 60px;
  color: #999;
  font-size: 12px;
}
.list-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 130px;
  flex-shrink: 0;
}
.icon-button {
  background: rgba(255, 255, 255, 0.08);
  color: #999;
  border: none;
  border-radius: 8px;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease, color 0.15s ease;
}
.icon-button:hover {
  background: rgba(255, 255, 255, 0.14);
  color: #ccc;
}
.icon-button.active {
  color: #d68a34;
  background: rgba(214, 138, 52, 0.16);
}

/* Detail (list + preview) view — a bounded-height split panel so the list
   and the preview each get their own scrollbar instead of the whole page
   scrolling as one long column */
.detail-view {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 20px;
  align-items: start;
  height: calc(100vh - 262px);
  min-height: 420px;
}
.detail-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}
.detail-list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: none;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 8px;
  cursor: pointer;
  color: #ccc;
  text-align: left;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}
.detail-list-item:hover {
  background: rgba(255, 255, 255, 0.05);
  transform: translateX(2px);
}
.detail-list-item.active {
  background: rgba(214, 138, 52, 0.16);
  border-color: rgba(214, 138, 52, 0.5);
  color: #fff;
  box-shadow: 0 4px 16px rgba(214, 138, 52, 0.15);
}
.detail-list-thumb {
  width: 40px;
  height: 54px;
  object-fit: cover;
  border-radius: 6px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
  flex-shrink: 0;
}
.detail-preview {
  border: 1px solid #2a2a2a;
  border-radius: 16px;
  background: rgba(0, 0, 0, 0.3);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
  height: 100%;
  overflow-y: auto;
}
.preview-banner {
  position: relative;
  height: 260px;
  background-size: cover;
  background-position: center;
}
.preview-banner-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(18, 18, 18, 0) 40%, rgba(18, 18, 18, 0.95) 100%);
}
.preview-info {
  padding: 20px;
}
.preview-info h2 {
  margin: 0 0 10px;
}
.preview-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.preview-badge {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 5px 14px;
  border-radius: 999px;
  font-size: 12px;
  text-transform: capitalize;
  color: #ccc;
}
.preview-details {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 18px;
  padding-top: 14px;
  border-top: 1px solid #2a2a2a;
}
.preview-platforms {
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: #ddd;
  font-size: 13px;
}
.preview-links {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.preview-links a {
  color: #d68a34;
  font-size: 13px;
  text-decoration: none;
}
.preview-links a:hover {
  text-decoration: underline;
}
.preview-detail-row {
  display: flex;
  gap: 10px;
  font-size: 13px;
  color: #ddd;
  align-items: baseline;
}
.preview-detail-label {
  color: #888;
  min-width: 80px;
  flex-shrink: 0;
}
.preview-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.preview-pill {
  background: #2a2a2a;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  color: #ccc;
}
.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity 0.2s ease;
}
.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
}
.preview-badge.score {
  color: #d68a34;
}
.preview-description-html {
  color: #ccc;
  line-height: 1.6;
  margin: 0 0 18px;
  max-width: 100%;
  overflow-wrap: break-word;
}
.preview-description-html :deep(img),
.preview-description-html :deep(video) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 10px 0;
  display: block;
}
.preview-description-html :deep(h1),
.preview-description-html :deep(h2),
.preview-description-html :deep(h3) {
  margin: 18px 0 6px;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}
.preview-description-html :deep(p) {
  margin: 0 0 12px;
}
.preview-description-html :deep(a) {
  color: #d68a34;
}
.preview-description-html :deep(ul) {
  padding-left: 20px;
  margin: 0 0 12px;
}
.preview-actions {
  display: flex;
  gap: 10px;
}
.empty-row {
  color: #777;
  font-size: 14px;
}

/* Shared buttons */
.primary-button,
.secondary-button,
.small-button,
.danger-button {
  border: none;
  border-radius: 8px;
  padding: 9px 16px;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.primary-button {
  background: #d68a34;
  color: #111;
}
.secondary-button,
.small-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.danger-button {
  background: rgba(220, 38, 38, 0.18);
  color: #fca5a5;
}
.danger-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Confirm dialog */
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
</style>
