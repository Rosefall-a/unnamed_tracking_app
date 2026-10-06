<script setup lang="ts">
import { sizedAssetUrl } from "../utils/gameImages";
import HeartIcon from "../components/HeartIcon.vue";
import GameCard from "../components/GameCard.vue";
import CheckIcon from "../components/CheckIcon.vue";
import GameFormModal from "../components/GameFormModal.vue";
import BulkEditModal from "../components/BulkEditModal.vue";
import RandomGamePicker from "../components/RandomGamePicker.vue";
import FilterCombobox from "../components/FilterCombobox.vue";
import CollectionPickerModal from "../components/CollectionPickerModal.vue";
import GameTopBar from "../components/GameTopBar.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import type { ViewMode, CardDensity } from "../composables/useGameLibrary";
import { useGameLibrary } from "../composables/useGameLibrary";
import { computed, ref } from "vue";
import { quickTourActive } from "../state/quickTour";
const {
  viewportWidth,
  activePriority,
  priorityLabel,
  formatDisplayDate,
  computeScore,
  games,
  loading,
  error,
  showFormModal,
  editingGame,
  deletingGame,
  deleting,
  deleteError,
  viewMode,
  selectedGame,
  gridFocusIndex,
  selectMode,
  selectedIds,
  showBulkEditModal,
  showRandomPicker,
  showBulkEditHint,
  dismissBulkEditHint,
  toggleSelectMode,
  toggleSelect,
  clearSelection,
  onBulkEditSaved,
  bulkEditResultCount,
  bulkAddingToCollection,
  bulkAddToCollection,
  selectedGameDescriptionHtml,
  searchQuery,
  statusFilter,
  platformFilter,
  genreFilter,
  sortBy,
  showAdvancedFilters,
  franchiseFilter,
  collectionFilter,
  companyFilter,
  ageRatingFilter,
  regionFilter,
  languageFilter,
  metadataProviderFilter,
  favoritesOnly,
  achievementsFilter,
  retroAchievementsOnly,
  missingFilter,
  tagsFilter,
  toggleTagFilter,
  recentSearches,
  showRecentSearches,
  commitSearchToRecent,
  pickRecentSearch,
  removeRecentSearch,
  advancedFilterCount,
  filterCount,
  clearAdvancedFilters,
  clearAllFilters,
  filterPresets,
  showPresetsMenu,
  saveCurrentAsPreset,
  applyPreset,
  deletePreset,
  statusOptions,
  VIEW_OPTIONS,
  statusCounts,
  platformOptions,
  platformExtraOptions,
  genreOptions,
  franchiseOptions,
  collectionOptions,
  companyOptions,
  ageRatingOptions,
  regionOptions,
  languageOptions,
  metadataProviderOptions,
  setView,
  openAddModal,
  openEditModal,
  onGameSaved,
  onDeleteFromModal,
  toggleFavorite,
  collectionPickerGame,
  handleAddToCollection,
  onCollectionAdded,
  confirmDelete,
  totalPlaytime,
  gameLastPlayed,
  openGame,
  filteredGames,
  hasAnyGames,
  isEmpty,
  searchSuggestions,
  activeFilterPills,
  cardDensity,
  CARD_COLUMNS,
  rankByGameId,
  rowVirtualizer,
  cardsInRow,
} = useGameLibrary();
const previewToolsOpen = ref(false);
const compactControls = computed(
  () =>
    viewportWidth.value <= 760 &&
    !previewToolsOpen.value &&
    !quickTourActive.value &&
    !selectMode.value,
);
const compactPreview = computed(
  () => compactControls.value && viewMode.value === "detail",
);
</script>

<template>
  <main
    class="library"
    :class="{
      locked: viewMode === 'detail',
      'compact-preview': compactPreview,
      'compact-controls': compactControls,
    }"
    :data-shortcut-context="
      viewMode === 'detail'
        ? 'games.preview'
        : viewMode === 'cards'
          ? 'games.cards'
          : undefined
    "
  >
    <GameTopBar active="games">
      <template #actions>
        <SegmentedTabs
          :options="VIEW_OPTIONS"
          :model-value="viewMode"
          aria-label="View"
          @update:model-value="setView($event as ViewMode)"
        />
      </template>
    </GameTopBar>

    <div ref="libraryContent" class="content">
      <div class="page-head">
        <div>
          <h1>Games</h1>
          <div class="sub">
            {{ games.length }} {{ games.length === 1 ? "game" : "games" }}
          </div>
        </div>
        <button
          v-if="viewportWidth <= 760"
          type="button"
          class="secondary-button preview-tools-toggle"
          :aria-expanded="!compactControls"
          :aria-label="compactControls ? 'Library controls' : 'Hide controls'"
          @click="previewToolsOpen = !previewToolsOpen"
        >
          {{ compactControls ? "Controls" : "Hide controls" }}
        </button>
        <div class="head-actions">
          <div class="select-button-wrap">
            <button
              type="button"
              class="select-btn"
              :class="{ on: selectMode }"
              @click="
                toggleSelectMode();
                dismissBulkEditHint();
              "
            >
              {{ selectMode ? "Done" : "Select" }}
            </button>
          </div>
          <button
            type="button"
            class="select-btn"
            :disabled="!games.length"
            title="Pick a game to play, filtered by status, platform, genre, length and priority"
            @click="showRandomPicker = true"
          >
            Random
          </button>
          <button
            type="button"
            class="add-btn"
            data-shortcut="create"
            @click="openAddModal"
          >
            + Add Game
          </button>
        </div>
      </div>

      <div v-if="showBulkEditHint && !compactControls" class="first-use-hint">
        <span
          >Select games, then bulk-edit their status, tags, or collections all
          at once.</span
        >
        <button
          type="button"
          class="first-use-hint-dismiss"
          @click="dismissBulkEditHint"
        >
          Got it
        </button>
      </div>

      <div v-if="selectMode" class="bulk-toolbar">
        <span class="count">{{ selectedIds.size }} selected</span>
        <button
          type="button"
          class="btn-outline"
          :disabled="filteredGames.length === 0"
          @click="selectedIds = new Set(filteredGames.map((g) => g.id))"
        >
          Select all ({{ filteredGames.length }})
        </button>
        <button
          type="button"
          class="btn-outline"
          :disabled="!selectedIds.size"
          @click="clearSelection"
        >
          Clear
        </button>
        <button
          type="button"
          class="btn-outline"
          :disabled="!selectedIds.size || bulkAddingToCollection"
          @click="bulkAddToCollection"
        >
          {{ bulkAddingToCollection ? "Adding…" : "Add to Collection" }}
        </button>
        <button
          type="button"
          class="btn-solid"
          :disabled="!selectedIds.size"
          @click="showBulkEditModal = true"
        >
          Bulk Edit
        </button>
      </div>
      <div
        v-if="bulkEditResultCount !== null"
        class="form-success bulk-success"
      >
        Updated {{ bulkEditResultCount }} game{{
          bulkEditResultCount === 1 ? "" : "s"
        }}.
      </div>

      <div class="toolbar">
        <div class="search-wrap">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <circle cx="11" cy="11" r="7" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref="librarySearch"
            data-shortcut="search"
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="Search your library… (/)"
            aria-label="Search games"
            @focus="showRecentSearches = true"
            @blur="
              showRecentSearches = false;
              commitSearchToRecent();
            "
            @keydown.enter="commitSearchToRecent"
          />
          <div
            v-if="
              showRecentSearches && !searchQuery.trim() && recentSearches.length
            "
            class="recent-searches-dropdown"
          >
            <div class="recent-searches-label">Recent searches</div>
            <button
              v-for="q in recentSearches"
              :key="q"
              type="button"
              class="recent-search-item"
              @mousedown.prevent="pickRecentSearch(q)"
            >
              <span>{{ q }}</span>
              <span
                class="recent-search-remove"
                @mousedown.prevent.stop="removeRecentSearch(q)"
                >✕</span
              >
            </button>
          </div>
        </div>
        <select v-model="sortBy" class="sort-select" aria-label="Sort by">
          <option value="name">Name (A–Z)</option>
          <option value="name_desc">Name (Z–A)</option>
          <option value="recent">Recently added</option>
          <option value="rating">Rating</option>
          <option value="playtime">Most Played</option>
          <option value="last_played">Recently played</option>
          <option value="neglected">Neglected (least recently played)</option>
          <option value="priority">Priority</option>
          <option value="release">Release date (newest)</option>
          <option value="length">Time to beat (shortest)</option>
        </select>
        <button
          type="button"
          class="filter-btn"
          data-tour="games-filters"
          :class="{ 'active-filter': filterCount }"
          @click="showAdvancedFilters = !showAdvancedFilters"
        >
          Filters
          <span v-if="filterCount" class="count">{{ filterCount }}</span>
        </button>
        <div class="presets-wrap">
          <button
            type="button"
            class="filter-btn"
            @click="showPresetsMenu = !showPresetsMenu"
          >
            Presets
          </button>
          <div v-if="showPresetsMenu" class="presets-dropdown">
            <button
              v-for="p in filterPresets"
              :key="p.name"
              type="button"
              class="preset-item"
              @click="applyPreset(p)"
            >
              <span>{{ p.name }}</span>
              <span class="preset-remove" @click.stop="deletePreset(p.name)"
                >✕</span
              >
            </button>
            <p v-if="!filterPresets.length" class="preset-empty">
              No saved presets yet.
            </p>
            <button
              type="button"
              class="preset-save"
              @click="saveCurrentAsPreset"
            >
              + Save current filters
            </button>
          </div>
        </div>
        <div
          v-if="viewMode === 'cards'"
          class="density-toggle"
          title="Card size"
        >
          <button
            v-for="d in ['compact', 'cozy', 'large'] as CardDensity[]"
            :key="d"
            type="button"
            class="density-button"
            :class="{ active: cardDensity === d }"
            :title="d"
            @click="cardDensity = d"
          >
            {{ d === "compact" ? "S" : d === "cozy" ? "M" : "L" }}
          </button>
        </div>
      </div>

      <div
        v-if="showAdvancedFilters"
        class="advanced-panel"
        data-tour="games-filter-panel"
      >
        <div class="filter-group platform-genre-group">
          <FilterCombobox
            v-model="platformFilter"
            :options="platformOptions"
            :extra-options="platformExtraOptions"
            extra-label="Retro"
            placeholder="Platform"
            all-label="All platforms"
          />
          <FilterCombobox
            v-model="genreFilter"
            :options="genreOptions"
            placeholder="Genre"
            all-label="All genres"
          />
        </div>
        <div class="advanced-field">
          <label>Franchise</label>
          <FilterCombobox
            v-model="franchiseFilter"
            :options="franchiseOptions"
            placeholder="Franchise"
            all-label="All franchises"
          />
        </div>
        <div class="advanced-field">
          <label>Collection</label>
          <FilterCombobox
            v-model="collectionFilter"
            :options="collectionOptions"
            placeholder="Collection"
            all-label="All collections"
          />
        </div>
        <div class="advanced-field">
          <label>Company</label>
          <FilterCombobox
            v-model="companyFilter"
            :options="companyOptions"
            placeholder="Company"
            all-label="All companies"
          />
        </div>
        <div class="advanced-field">
          <label>Age Rating</label>
          <FilterCombobox
            v-model="ageRatingFilter"
            :options="ageRatingOptions"
            placeholder="Age rating"
            all-label="All ratings"
          />
        </div>
        <div class="advanced-field">
          <label>Region</label>
          <FilterCombobox
            v-model="regionFilter"
            :options="regionOptions"
            placeholder="Region"
            all-label="All regions"
          />
        </div>
        <div class="advanced-field">
          <label>Language</label>
          <FilterCombobox
            v-model="languageFilter"
            :options="languageOptions"
            placeholder="Language"
            all-label="All languages"
          />
        </div>
        <div class="advanced-field">
          <label>Metadata Provider</label>
          <FilterCombobox
            v-model="metadataProviderFilter"
            :options="metadataProviderOptions"
            placeholder="Provider"
            all-label="All providers"
          />
        </div>
        <div class="advanced-field">
          <label>Achievements</label>
          <select
            v-model="achievementsFilter"
            class="filter-select"
            aria-label="Achievements"
          >
            <option value="all">All games</option>
            <option value="has">Has achievements</option>
            <option value="none">No achievements</option>
          </select>
        </div>
        <div class="advanced-field">
          <label>What's missing</label>
          <select
            v-model="missingFilter"
            class="filter-select"
            aria-label="What's missing"
          >
            <option value="none">Nothing, show everything</option>
            <option value="playtime">No playtime logged</option>
            <option value="rating">No rating</option>
            <option value="tags">No tags</option>
            <option value="description">No description</option>
          </select>
        </div>
        <div class="advanced-field advanced-field-wide">
          <label>Tags (any of)</label>
          <div class="tags-multiselect">
            <button
              v-for="tag in genreOptions"
              :key="tag"
              type="button"
              class="tag-chip"
              :class="{ active: tagsFilter.includes(tag) }"
              @click="toggleTagFilter(tag)"
            >
              {{ tag }}
            </button>
          </div>
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
          <button
            type="button"
            class="clear-advanced"
            :disabled="!advancedFilterCount"
            @click="clearAdvancedFilters"
          >
            Clear advanced filters
          </button>
        </div>
      </div>

      <div class="status-tabs">
        <button
          v-for="s in statusOptions"
          :key="s"
          type="button"
          class="status-tab"
          :class="{ active: statusFilter === s }"
          @click="statusFilter = s"
        >
          {{ s === "all" ? "All" : s }}
          <span class="n">{{ statusCounts[s] }}</span>
        </button>
      </div>

      <div v-if="activeFilterPills.length" class="active-filter-pills">
        <button
          v-for="pill in activeFilterPills"
          :key="pill.key"
          type="button"
          class="filter-pill"
          :title="`Remove ${pill.label} filter`"
          @click="pill.clear()"
        >
          {{ pill.label }} <span class="filter-pill-x">✕</span>
        </button>
        <button
          type="button"
          class="filter-pill-clear-all"
          @click="clearAllFilters"
        >
          Clear all
        </button>
      </div>

      <p v-if="loading" class="empty-state">Loading…</p>
      <p v-else-if="error" class="empty-state error">{{ error }}</p>

      <div v-else-if="isEmpty" class="empty-state rich">
        <svg
          v-if="!hasAnyGames"
          viewBox="0 0 24 24"
          width="48"
          height="48"
          fill="none"
          stroke="currentColor"
          stroke-width="1.4"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <path d="M3 9h18" />
          <path d="M8 13h.01M12 13h.01M16 13h.01" />
        </svg>
        <h3 v-if="!hasAnyGames">Your library is empty</h3>
        <p>
          {{
            hasAnyGames
              ? "Nothing matches. Try a different filter or search."
              : "Add your first game to get started."
          }}
        </p>
        <div v-if="searchSuggestions.length" class="search-suggestions">
          <span>Did you mean:</span>
          <button
            v-for="s in searchSuggestions"
            :key="s"
            type="button"
            class="search-suggestion-item"
            @click="searchQuery = s"
          >
            {{ s }}
          </button>
        </div>
        <button
          v-if="hasAnyGames"
          type="button"
          class="btn-outline"
          @click="clearAllFilters"
        >
          Clear filters
        </button>
        <template v-else>
          <button
            type="button"
            class="btn-solid"
            data-shortcut="create"
            @click="openAddModal"
          >
            + Add Game
          </button>
          <ul class="empty-hint-list">
            <li>
              Add a game manually, or connect Steam/GOG/PlayStation in Settings
              to sync a library
            </li>
            <li>
              Drop screenshots or files into Upload and assign them to a game
              later
            </li>
          </ul>
        </template>
      </div>

      <template v-else>
        <div
          v-if="viewMode === 'cards'"
          class="grid-virtual-container"
          :style="{ height: rowVirtualizer.getTotalSize() + 'px' }"
        >
          <div
            v-for="virtualRow in rowVirtualizer.getVirtualItems()"
            :key="virtualRow.index"
            :ref="(el) => rowVirtualizer.measureElement(el as HTMLElement)"
            :data-index="virtualRow.index"
            class="grid-row"
            :style="{
              transform: `translateY(${virtualRow.start}px)`,
              gridTemplateColumns: `repeat(${CARD_COLUMNS}, 1fr)`,
            }"
          >
            <GameCard
              v-for="(game, colIndex) in cardsInRow(virtualRow.index)"
              :key="game.id"
              :game="game"
              :rank="rankByGameId.get(game.id) ?? null"
              :select-mode="selectMode"
              :selected="selectedIds.has(game.id)"
              :keyboard-focused="
                gridFocusIndex === virtualRow.index * CARD_COLUMNS + colIndex
              "
              @edit="openEditModal"
              @add-to-collection="handleAddToCollection"
              @toggle-select="toggleSelect"
            />
          </div>
        </div>

        <div v-else-if="viewMode === 'list'" class="list-view">
          <div v-if="filteredGames.length" class="list-header">
            <span></span>
            <button
              type="button"
              class="sortable left"
              :class="{ active: sortBy === 'name' }"
              @click="sortBy = 'name'"
            >
              Name
            </button>
            <span></span>
            <button
              type="button"
              class="sortable"
              :class="{ active: sortBy === 'playtime' }"
              @click="sortBy = 'playtime'"
            >
              Playtime
            </button>
            <button
              type="button"
              class="sortable"
              :class="{ active: sortBy === 'rating' }"
              @click="sortBy = 'rating'"
            >
              Rating
            </button>
            <span>Rank</span>
            <button
              type="button"
              class="sortable"
              :class="{ active: sortBy === 'neglected' }"
              @click="sortBy = 'neglected'"
            >
              Last played
            </button>
            <span>Released</span>
            <span>Status</span>
          </div>
          <div
            v-for="game in filteredGames"
            :key="game.id"
            class="list-row"
            @click="selectMode ? toggleSelect(game) : openGame(game)"
          >
            <div class="list-thumb-wrap">
              <img
                class="list-cover"
                :src="game.coverImageUrl"
                alt=""
                loading="lazy"
                decoding="async"
              />
              <div
                v-if="selectMode"
                class="select-checkbox"
                :class="{ checked: selectedIds.has(game.id) }"
                @click.stop="toggleSelect(game)"
              >
                <CheckIcon v-if="selectedIds.has(game.id)" />
              </div>
            </div>
            <div class="list-title-col">
              <div class="list-title">{{ game.title }}</div>
              <div class="list-sub">
                {{ game.tags[0] ?? "No genre"
                }}<template v-if="game.platforms[0]">
                  · {{ game.platforms[0].platform }}</template
                >
              </div>
            </div>
            <div class="icon-cluster">
              <button
                type="button"
                class="icon-btn"
                :class="{ active: game.favorite }"
                :title="
                  game.favorite ? 'Remove from favorites' : 'Add to favorites'
                "
                @click.stop="toggleFavorite(game)"
              >
                <HeartIcon :filled="game.favorite" />
              </button>
              <button
                type="button"
                class="icon-btn"
                title="Add to collection"
                @click.stop="handleAddToCollection(game)"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                </svg>
              </button>
              <button
                type="button"
                class="icon-btn"
                title="Edit"
                @click.stop="openEditModal(game)"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
                </svg>
              </button>
            </div>
            <div class="stat-cell strong">
              {{ totalPlaytime(game) === "N/A" ? "–" : totalPlaytime(game) }}
            </div>
            <div class="score-cell" :class="{ empty: !computeScore(game) }">
              {{
                computeScore(game)
                  ? `★ ${computeScore(game)!.sum.toFixed(1)}`
                  : "–"
              }}
            </div>
            <div class="rank-cell">
              <span v-if="rankByGameId.get(game.id)" class="rank-badge"
                >#{{ rankByGameId.get(game.id) }}</span
              >
              <span v-else class="rank-empty">–</span>
            </div>
            <div class="stat-cell">
              {{
                gameLastPlayed(game)
                  ? new Date(gameLastPlayed(game)!).toLocaleDateString()
                  : "–"
              }}
            </div>
            <div class="stat-cell">
              {{ game.releaseDate ? formatDisplayDate(game.releaseDate) : "–" }}
            </div>
            <div class="status-cell">
              <span
                class="status-pill"
                :class="`st-${game.status.replace(' ', '-')}`"
                >{{ game.status }}</span
              >
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
              <img
                class="detail-list-thumb"
                :src="game.coverImageUrl"
                alt=""
                loading="lazy"
                decoding="async"
              />
              <span>{{ game.title }}</span>
            </button>
          </div>

          <Transition name="preview-fade" mode="out-in">
            <div
              v-if="selectedGame"
              :key="selectedGame.id"
              class="detail-preview"
            >
              <div
                class="preview-banner"
                :style="{
                  backgroundImage: `url(${sizedAssetUrl(selectedGame.bannerImageUrl, 800)})`,
                }"
              >
                <div class="preview-banner-overlay"></div>
              </div>
              <div class="preview-info">
                <h2>{{ selectedGame.title }}</h2>
                <div class="preview-meta">
                  <span class="preview-badge">{{ selectedGame.status }}</span>
                  <span
                    v-if="computeScore(selectedGame)"
                    class="preview-badge score"
                  >
                    ★ {{ computeScore(selectedGame)!.sum.toFixed(1) }}
                  </span>
                  <span class="preview-badge">{{
                    totalPlaytime(selectedGame)
                  }}</span>
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
                  <div
                    v-if="selectedGame.releaseDate"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Released</span>
                    <span>{{
                      formatDisplayDate(selectedGame.releaseDate)
                    }}</span>
                  </div>
                  <div
                    v-if="activePriority(selectedGame) !== null"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Priority</span>
                    <span>{{
                      priorityLabel(activePriority(selectedGame)!)
                    }}</span>
                  </div>
                  <div v-if="selectedGame.dateAdded" class="preview-detail-row">
                    <span class="preview-detail-label">Added</span>
                    <span>{{
                      new Date(selectedGame.dateAdded).toLocaleDateString()
                    }}</span>
                  </div>
                  <div
                    v-if="selectedGame.platforms.length"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Platforms</span>
                    <div class="preview-platforms">
                      <div
                        v-for="p in selectedGame.platforms"
                        :key="p.platform"
                      >
                        {{ p.platform }}:
                        {{ Math.round(p.playtimeMinutes / 60) }}h
                        <span v-if="p.completionPercent !== null"
                          >· {{ p.completionPercent }}%</span
                        >
                      </div>
                    </div>
                  </div>
                  <div
                    v-if="selectedGame.tags.length"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Tags</span>
                    <span class="preview-pills">
                      <span
                        v-for="tag in selectedGame.tags"
                        :key="tag"
                        class="preview-pill"
                        >{{ tag }}</span
                      >
                    </span>
                  </div>
                  <div
                    v-if="selectedGame.features.length"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Features</span>
                    <span class="preview-pills">
                      <span
                        v-for="f in selectedGame.features"
                        :key="f"
                        class="preview-pill"
                        >{{ f }}</span
                      >
                    </span>
                  </div>
                  <div
                    v-if="selectedGame.links.length"
                    class="preview-detail-row"
                  >
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
                    v-if="
                      selectedGame.ownership.format ||
                      selectedGame.ownership.price !== null
                    "
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Ownership</span>
                    <span>
                      {{ selectedGame.ownership.format ?? "N/A" }}
                      <span v-if="selectedGame.ownership.price !== null">
                        · {{ selectedGame.ownership.priceCurrency ?? "USD" }}
                        {{ selectedGame.ownership.price.toFixed(2) }}
                      </span>
                    </span>
                  </div>
                  <div
                    v-if="selectedGame.folderLocation"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Folder</span>
                    <span>{{ selectedGame.folderLocation }}</span>
                  </div>
                </div>
                <div
                  v-if="selectedGameDescriptionHtml"
                  class="preview-description-html"
                  v-html="selectedGameDescriptionHtml"
                ></div>
                <div class="preview-actions">
                  <button
                    type="button"
                    class="primary-button"
                    @click="openGame(selectedGame)"
                  >
                    Open Full Page
                  </button>
                  <button
                    type="button"
                    class="secondary-button"
                    @click="openEditModal(selectedGame)"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    class="icon-button"
                    title="Add to collection"
                    @click="handleAddToCollection(selectedGame)"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      width="16"
                      height="16"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path
                        d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"
                      />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="icon-button"
                    :class="{ active: selectedGame.favorite }"
                    :title="
                      selectedGame.favorite
                        ? 'Remove from favorites'
                        : 'Add to favorites'
                    "
                    @click="toggleFavorite(selectedGame)"
                  >
                    <HeartIcon :filled="selectedGame.favorite" />
                  </button>
                </div>
              </div>
            </div>
          </Transition>
          <p v-if="!selectedGame" class="empty-row">
            Select a game to preview it.
          </p>
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

      <BulkEditModal
        v-if="showBulkEditModal"
        :game-ids="Array.from(selectedIds)"
        @close="showBulkEditModal = false"
        @saved="onBulkEditSaved"
      />

      <RandomGamePicker
        v-if="showRandomPicker"
        :games="games"
        @close="showRandomPicker = false"
      />

      <div
        v-if="deletingGame"
        class="confirm-backdrop"
        @click.self="deletingGame = null"
      >
        <div class="confirm-dialog">
          <h3>Delete {{ deletingGame.title }}?</h3>
          <p>
            Moved to trash, recoverable for 7 days from Settings, then purged
            for good.
          </p>
          <div v-if="deleteError" class="confirm-error">{{ deleteError }}</div>
          <div class="confirm-actions">
            <button
              type="button"
              class="secondary-button"
              @click="deletingGame = null"
            >
              Cancel
            </button>
            <button
              type="button"
              class="danger-button"
              :disabled="deleting"
              @click="confirmDelete"
            >
              {{ deleting ? "Deleting…" : "Delete" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped src="../styles/pages/game-library.css" />
