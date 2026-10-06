<script setup lang="ts">
import PluginExtensionSlot from "../components/plugins/PluginExtensionSlot.vue";
import PluginContextualActions from "../components/plugins/PluginContextualActions.vue";
import { formatDisplayDate } from "../utils/dates";
import { activePriority, priorityLabel } from "../utils/priority";
import { HERO_WIDTH, POSTER_WIDTH, sizedAssetUrl } from "../utils/gameImages";
import type { TrashedGameFile } from "../services/media";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import GameMediaPanel from "../components/GameMediaPanel.vue";
import { normalizePlatformFamily } from "../utils/platforms";
import GameArchivesPanel from "../components/GameArchivesPanel.vue";
import ArchiveCard from "../components/ArchiveCard.vue";
import ArchiveEditDialog from "../components/ArchiveEditDialog.vue";
import GameNotesPanel from "../components/GameNotesPanel.vue";
import GameStatsPanel from "../components/GameStatsPanel.vue";
import type { GameStatus } from "../types/game";
import GameFormModal from "../components/GameFormModal.vue";
import GameRatingPicker from "../components/GameRatingPicker.vue";
import GameCollectionsButton from "../components/GameCollectionsButton.vue";
import BackButton from "../components/BackButton.vue";
import GameTopBar from "../components/GameTopBar.vue";
import HeartIcon from "../components/HeartIcon.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import {
  isUnlocked,
  formatPercent,
  unlockedOn,
  KIND_LABEL,
} from "../utils/achievements";
import type { AchFilter } from "../composables/useGameAchievements";
import GameAccountsPanel from "../components/game/GameAccountsPanel.vue";
import GameWorldMapPanel from "../components/game/GameWorldMapPanel.vue";
import { provide } from "vue";
import { useGameDetail } from "../composables/useGameDetail";
import { gameDetailKey } from "../composables/gameDetailContext";
const model = useGameDetail();
provide(gameDetailKey, model);
const {
  route,
  goBackToLibrary,
  game,
  loading,
  error,
  showEditModal,
  deleting,
  deleteError,
  showDeleteConfirm,
  descriptionHtml,
  descriptionExpanded,
  descriptionOverflows,
  parentGameTitle,
  RELATIONSHIP_LABELS,
  variants,
  profiles,
  onGameSaved,
  resumeNoteDraft,
  resumeNoteEditing,
  resumeNoteSaving,
  resumeNoteError,
  startEditResumeNote,
  saveResumeNote,
  loggingPlaytime,
  logPlaytime,
  similarGames,
  toggleFavorite,
  STATUS_OPTIONS,
  changeStatus,
  onCollectionsChanged,
  onRatingsChange,
  onDeleteFromModal,
  confirmDelete,
  recentActivity,
  heroCredits,
  libraryLink,
  ratingParts,
  overviewFacts,
  mainTags,
  moreTags,
  activeTab,
  pageSettings,
  visibleTabs,
  moreTabs,
  showMoreTabs,
  openMoreTab,
  achievementsOn,
  tieAchievements,
  mediaItems,
  mediaError,
  mediaLoadedFor,
  screenshots,
  clips,
  soundtrackItems,
  lightboxUrl,
  mediaByAchievement,
  achMediaOpen,
  toggleAchMedia,
  uploadingMedia,
  onMediaFilesSelected,
  openAchievement,
  keepThumbnail,
  removeMedia,
  activeTabTrash,
  restoreMediaItem,
  saveMediaItem,
  bulkSaveMedia,
  bulkDeleteMedia,
  detectOne,
  detectMany,
  docsFiles,
  filesLoaded,
  filesError,
  uploadingFiles,
  fieldChanges,
  fieldChangesLoading,
  fieldChangesError,
  onGameFilesSelected,
  saveGameFile,
  bulkSaveFiles,
  removeGameFile,
  docsTrash,
  restoreFileItem,
  saveArchives,
  saveArchivesLoaded,
  saveUploading,
  onNewSaveSelected,
  onAddSaveVersion,
  editingArchive,
  editingArchiveLive,
  openArchiveEdit,
  saveArchiveDetails,
  bulkDeleteArchives,
  onDeleteArchive,
  saveTrash,
  onRestoreArchive,
  onDeleteVersion,
  onAddWorldVersion,
  descriptionOf,
  achFilter,
  achProvider,
  achSearch,
  achLocal,
  noteOpen,
  noteDraft,
  overallOpen,
  overallDraft,
  isPinned,
  togglePin,
  isHiddenLocked,
  revealAchievement,
  hideAchievement,
  toggleNote,
  saveNote,
  clearNote,
  toggleOverall,
  saveOverall,
  unlockedCount,
  achFilterOptions,
  sortBy,
  sortMark,
  ariaSort,
  mobileSort,
  achProviders,
  shownAchievements,
  achStats,
  formatPlaytime,
} = model;
</script>
<template>
  <main
    v-if="loading"
    class="game-detail-page detail loading-state"
    aria-busy="true"
  >
    <GameTopBar active="games" />
    <!-- the shape of the real page: hero with poster, title, badges and
         buttons, then the tabs, then the first block of content -->
    <section class="hero">
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <SkeletonBlock width="212px" height="307px" radius="8px" />
        <div class="hero-text detail-skeleton-text">
          <SkeletonBlock width="30%" height="12px" />
          <SkeletonBlock width="60%" height="40px" />
          <div class="game-detail-page detail-skeleton-row">
            <SkeletonBlock
              v-for="w in [64, 96, 80, 72]"
              :key="w"
              :width="`${w}px`"
              height="24px"
              radius="999px"
            />
          </div>
          <div class="game-detail-page detail-skeleton-row">
            <SkeletonBlock width="88px" height="36px" radius="8px" />
            <SkeletonBlock width="36px" height="36px" radius="8px" />
            <SkeletonBlock width="36px" height="36px" radius="8px" />
          </div>
        </div>
      </div>
    </section>
    <div class="tabbar-wrap">
      <SkeletonBlock width="470px" height="44px" radius="10px" />
    </div>
    <div class="game-detail-page detail-skeleton-body">
      <div class="game-detail-page detail-skeleton-row">
        <SkeletonBlock
          v-for="i in 4"
          :key="i"
          width="120px"
          height="44px"
          radius="8px"
        />
      </div>
      <SkeletonBlock height="14px" />
      <SkeletonBlock height="14px" width="92%" />
      <SkeletonBlock height="14px" width="70%" />
    </div>
  </main>

  <main v-else-if="error" class="game-detail-page detail error-state">
    <GameTopBar active="games" />
    <p>{{ error }}</p>
  </main>

  <main v-else-if="game" class="game-detail-page detail">
    <PluginExtensionSlot
      slot-id="game.overview.after-header"
      :context="{ host_page: 'game.overview', game_id: game.id }"
    />
    <PluginContextualActions
      :context="{ kind: 'game', resource_id: game.id }"
    />
    <GameTopBar active="games" />

    <BackButton class="back-spot" @click="goBackToLibrary" />

    <GameFormModal
      v-if="showEditModal"
      :game="game"
      @close="showEditModal = false"
      @saved="onGameSaved"
      @delete="onDeleteFromModal"
    />

    <ArchiveEditDialog
      v-if="editingArchive && editingArchiveLive"
      :archive="editingArchiveLive"
      :noun="editingArchive.isWorld ? 'world' : 'save'"
      :uploading="saveUploading.has(editingArchive.id)"
      @close="editingArchive = null"
      @save="
        (a, patch) => saveArchiveDetails(a, editingArchive!.isWorld, patch)
      "
      @delete="onDeleteArchive($event, editingArchive!.isWorld)"
      @add-version="
        (a, files) =>
          editingArchive!.isWorld
            ? onAddWorldVersion(a, files)
            : onAddSaveVersion(a, files)
      "
      @delete-version="(a, v) => onDeleteVersion(a, v, editingArchive!.isWorld)"
    />

    <div
      v-if="showDeleteConfirm"
      class="confirm-backdrop"
      @click.self="showDeleteConfirm = false"
    >
      <div class="confirm-dialog">
        <h3>Delete {{ game.title }}?</h3>
        <p>This can't be undone.</p>
        <div v-if="deleteError" class="confirm-error">{{ deleteError }}</div>
        <div class="confirm-actions">
          <button
            type="button"
            class="secondary-button"
            @click="showDeleteConfirm = false"
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

    <section class="hero">
      <div
        class="hero-backdrop"
        :style="{
          backgroundImage: `url(${sizedAssetUrl(game.bannerImageUrl, HERO_WIDTH)})`,
        }"
      ></div>
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <div
          class="poster-card"
          :style="
            game.coverImageUrl
              ? {
                  backgroundImage: `url(${sizedAssetUrl(game.coverImageUrl, POSTER_WIDTH)})`,
                }
              : {}
          "
        >
          <span v-if="!game.coverImageUrl">{{ game.title }}</span>
        </div>
        <div class="hero-text">
          <router-link
            v-if="game.parentGameId"
            :to="`/games/${game.parentGameId}`"
            class="parent-breadcrumb"
          >
            {{ parentGameTitle ?? "…" }}
            <span v-if="game.relationshipType" class="relationship-tag">{{
              RELATIONSHIP_LABELS[game.relationshipType] ??
              game.relationshipType
            }}</span>
            →
          </router-link>
          <div
            v-if="heroCredits.length && !pageSettings.hide_credits"
            class="native-title"
          >
            <template v-for="(name, i) in heroCredits" :key="name">
              <span v-if="i" class="credit-dot"> · </span>
              <router-link
                class="filter-link"
                :to="libraryLink('company', name)"
                :title="`All games by ${name}`"
                >{{ name }}</router-link
              >
            </template>
          </div>
          <h1 class="title">{{ game.title }}</h1>
          <div class="badge-row">
            <select
              :value="game.status"
              class="badge status status-select"
              title="Change status"
              @change="
                changeStatus(
                  ($event.target as HTMLSelectElement).value as GameStatus,
                )
              "
            >
              <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">
                {{ s }}
              </option>
            </select>
            <GameRatingPicker
              v-if="!pageSettings.hide_rating"
              :model-value="{
                ratingOverall: game.ratingOverall,
                ratingStory: game.ratingStory,
                ratingGameplay: game.ratingGameplay,
                ratingSound: game.ratingSound,
              }"
              @change="onRatingsChange"
            />
            <span
              v-if="game.dateAdded && !pageSettings.hide_date_badge"
              class="badge"
            >
              {{ new Date(game.dateAdded).toLocaleDateString() }}
            </span>
            <router-link
              v-if="game.platforms.length && !pageSettings.hide_platform_badge"
              class="badge filter-badge"
              :to="libraryLink('platform', game.platforms[0].platform)"
              :title="`All ${normalizePlatformFamily(game.platforms[0].platform)} games`"
              >{{ game.platforms[0].platform }}</router-link
            >
            <button
              v-if="game.achievementTotal > 0 && achievementsOn"
              type="button"
              class="badge achievement-progress-badge"
              title="Jump to Achievements"
              @click="activeTab = 'Achievements'"
            >
              <svg
                viewBox="0 0 24 24"
                width="13"
                height="13"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M8 4h8v5a4 4 0 0 1-8 0z" />
                <path d="M8 4H5a2 2 0 0 0 0 4h1.5M16 4h3a2 2 0 0 1 0 4h-1.5" />
                <path d="M12 13v3" />
                <path d="M9 20h6" />
                <path d="M10 16.5h4l.8 3.5H9.2z" />
              </svg>
              {{ game.achievementPercent }}%
            </button>
            <span
              v-if="game.staleSince"
              class="badge stale-badge"
              :title="`Last sync (${new Date(game.staleSince).toLocaleDateString()}) no longer saw this in your ${game.source} library.`"
            >
              Not currently in your {{ game.source }} library
            </span>
          </div>
          <div class="action-row">
            <button
              class="edit-btn"
              type="button"
              @click="showEditModal = true"
            >
              ✎ Edit
            </button>
            <button
              v-if="!pageSettings.hide_favorite"
              class="icon-btn"
              :class="{ active: game.favorite }"
              type="button"
              :title="
                game.favorite ? 'Remove from favorites' : 'Add to favorites'
              "
              @click="toggleFavorite"
            >
              <HeartIcon :filled="game.favorite" />
            </button>
            <GameCollectionsButton
              v-if="!pageSettings.hide_collections"
              :game="game"
              @changed="onCollectionsChanged"
            />
          </div>
        </div>
      </div>
    </section>

    <div class="tabbar-wrap">
      <nav class="tabbar">
        <button
          v-for="tab in visibleTabs"
          :key="tab"
          type="button"
          class="tab-btn"
          :class="{ active: activeTab === tab }"
          @click="activeTab = tab"
        >
          {{ tab }}
        </button>
        <div v-if="moreTabs.length" class="tab-more">
          <button
            type="button"
            class="tab-btn tab-more-btn"
            title="Tabs with nothing in them yet"
            aria-haspopup="menu"
            :aria-expanded="showMoreTabs"
            @click.stop="showMoreTabs = !showMoreTabs"
          >
            +
          </button>
          <ul v-if="showMoreTabs" class="tab-more-menu" role="menu">
            <li v-for="tab in moreTabs" :key="tab">
              <button type="button" role="menuitem" @click="openMoreTab(tab)">
                {{ tab }}
              </button>
            </li>
          </ul>
        </div>
      </nav>
    </div>

    <section v-if="activeTab === 'Overview'" class="overview">
      <div v-if="overviewFacts.length" class="meta-block">
        <div v-if="overviewFacts.length" class="meta-grid">
          <div
            v-for="fact in overviewFacts"
            :key="fact.label"
            class="meta-item"
          >
            <span class="meta-label">{{ fact.label }}</span>
            <button
              v-if="fact.tab"
              type="button"
              class="meta-value meta-link"
              :class="{ accent: fact.accent, muted: fact.muted }"
              :title="`Open ${fact.tab}`"
              @click="activeTab = fact.tab"
            >
              {{ fact.value }}
            </button>
            <span
              v-else
              class="meta-value"
              :class="{ accent: fact.accent, muted: fact.muted }"
              >{{ fact.value }}</span
            >
          </div>
        </div>
      </div>

      <div v-if="mainTags.length" class="chip-row">
        <router-link
          v-for="tag in mainTags"
          :key="tag"
          class="chip primary chip-link"
          :to="libraryLink('tag', tag)"
          :title="`All ${tag} games`"
          >{{ tag }}</router-link
        >
      </div>

      <div v-if="descriptionHtml" class="description-block">
        <div
          class="description description-html"
          :class="{ clamped: descriptionOverflows && !descriptionExpanded }"
          v-html="descriptionHtml"
        ></div>
        <button
          v-if="descriptionOverflows"
          type="button"
          class="read-more-btn"
          @click="descriptionExpanded = !descriptionExpanded"
        >
          {{ descriptionExpanded ? "Show less" : "Read more" }}
        </button>
      </div>

      <section
        class="my-note"
        :class="{ empty: !game.resumeNote && !resumeNoteEditing }"
      >
        <template v-if="resumeNoteEditing">
          <header class="note-head">
            <h3>Where I left off</h3>
          </header>
          <textarea
            v-model="resumeNoteDraft"
            class="note-input"
            rows="3"
            placeholder="e.g. Just beat the third boss, about to start the desert region…"
            aria-label="Where I left off"
          ></textarea>
          <p v-if="resumeNoteError" class="note-error">
            {{ resumeNoteError }}
          </p>
          <div class="note-actions">
            <button
              type="button"
              class="btn-solid"
              :disabled="resumeNoteSaving"
              @click="saveResumeNote"
            >
              {{ resumeNoteSaving ? "Saving…" : "Save" }}
            </button>
            <button
              type="button"
              class="btn-text muted"
              @click="resumeNoteEditing = false"
            >
              Cancel
            </button>
          </div>
        </template>
        <template v-else-if="game.resumeNote">
          <header class="note-head">
            <h3>Where I left off</h3>
            <span class="note-private">Only you can see this</span>
            <button type="button" class="btn-text" @click="startEditResumeNote">
              Edit
            </button>
          </header>
          <p class="note-text">{{ game.resumeNote }}</p>
        </template>
        <template v-else>
          <button type="button" class="btn-text" @click="startEditResumeNote">
            + Add a note on where you left off
          </button>
          <span class="note-private">Only you can see this</span>
        </template>
      </section>

      <div v-if="variants.length" class="related-section">
        <div class="section-heading">
          <h2>Variants</h2>
        </div>
        <div class="poster-grid">
          <router-link
            v-for="variant in variants"
            :key="variant.id"
            :to="`/games/${variant.id}`"
            class="poster-card-sm"
          >
            <div
              class="poster-card-sm-art"
              :style="
                variant.coverImageUrl
                  ? {
                      backgroundImage: `url(${sizedAssetUrl(variant.coverImageUrl, POSTER_WIDTH)})`,
                    }
                  : {}
              "
            ></div>
            <div class="poster-card-sm-title">{{ variant.title }}</div>
            <div v-if="variant.relationshipType" class="poster-card-sm-meta">
              {{
                RELATIONSHIP_LABELS[variant.relationshipType] ??
                variant.relationshipType
              }}
            </div>
          </router-link>
        </div>
      </div>

      <div v-if="similarGames.length" class="related-section">
        <div class="section-heading">
          <h2>Similar games in your library</h2>
        </div>
        <div class="poster-grid">
          <router-link
            v-for="g in similarGames"
            :key="g.id"
            :to="`/games/${g.id}`"
            class="poster-card-sm"
          >
            <div
              class="poster-card-sm-art"
              :style="
                g.coverImageUrl
                  ? {
                      backgroundImage: `url(${sizedAssetUrl(g.coverImageUrl, POSTER_WIDTH)})`,
                    }
                  : {}
              "
            ></div>
            <div class="poster-card-sm-title">{{ g.title }}</div>
          </router-link>
        </div>
      </div>

      <details class="more-details">
        <summary>More details</summary>

        <div v-if="game.platforms.length" class="more-block">
          <h3 class="more-title">Platforms</h3>
          <ul class="platform-list">
            <li
              v-for="p in game.platforms"
              :key="p.platform"
              class="platform-item"
            >
              <div class="platform-top">
                <span class="platform-name">{{ p.platform }}</span>
                <span class="platform-hours">{{
                  formatPlaytime(p.playtimeMinutes)
                }}</span>
              </div>
              <div
                v-if="p.completionPercent !== null || p.lastPlayedAt"
                class="platform-sub"
              >
                <span v-if="p.completionPercent !== null"
                  >{{ p.completionPercent }}% complete</span
                >
                <span v-if="p.lastPlayedAt"
                  >last played
                  {{ new Date(p.lastPlayedAt).toLocaleDateString() }}</span
                >
              </div>
            </li>
          </ul>
          <button
            type="button"
            class="read-more-btn"
            :disabled="loggingPlaytime"
            title="Log a session just played, without editing the total by hand"
            @click="logPlaytime(30)"
          >
            + Log 30 min just played
          </button>
        </div>

        <div v-if="ratingParts.length" class="more-block">
          <h3 class="more-title">Your ratings</h3>
          <div class="kv-grid">
            <div v-for="part in ratingParts" :key="part.name" class="kv-row">
              <span class="kv-label">{{ part.name }}</span>
              <span class="kv-value accent">{{ part.value }}</span>
            </div>
          </div>
        </div>

        <div v-if="moreTags.length || game.features.length" class="more-block">
          <h3 class="more-title">Tags and features</h3>
          <div class="chip-row">
            <router-link
              v-for="tag in moreTags"
              :key="tag"
              class="chip chip-link"
              :to="libraryLink('tag', tag)"
              :title="`All ${tag} games`"
              >{{ tag }}</router-link
            >
            <span v-for="f in game.features" :key="f" class="chip">{{
              f
            }}</span>
          </div>
        </div>

        <div class="more-block">
          <h3 class="more-title">Library</h3>
          <div class="kv-grid">
            <div v-if="game.series" class="kv-row">
              <span class="kv-label">Series</span>
              <router-link
                class="kv-value filter-link"
                :to="libraryLink('series', game.series)"
                :title="`All games in ${game.series}`"
                >{{ game.series }}</router-link
              >
            </div>
            <div v-if="game.dateAdded" class="kv-row">
              <span class="kv-label">Added</span>
              <span class="kv-value">{{
                new Date(game.dateAdded).toLocaleDateString()
              }}</span>
            </div>
            <div v-if="recentActivity" class="kv-row">
              <span class="kv-label">Last played</span>
              <span class="kv-value">{{
                new Date(recentActivity).toLocaleDateString()
              }}</span>
            </div>
            <div v-if="game.source" class="kv-row">
              <span class="kv-label">Source</span>
              <span class="kv-value">{{ game.source }}</span>
            </div>
            <div v-if="activePriority(game) !== null" class="kv-row">
              <span class="kv-label">Priority</span>
              <span class="kv-value">{{
                priorityLabel(activePriority(game)!)
              }}</span>
            </div>
            <div v-if="game.ageRating" class="kv-row">
              <span class="kv-label">Age rating</span>
              <span class="kv-value">{{ game.ageRating }}</span>
            </div>
            <div v-if="game.region" class="kv-row">
              <span class="kv-label">Region</span>
              <span class="kv-value">{{ game.region }}</span>
            </div>
            <div v-if="game.language" class="kv-row">
              <span class="kv-label">Language</span>
              <span class="kv-value">{{ game.language }}</span>
            </div>
            <div v-if="game.achievementsProvider" class="kv-row">
              <span class="kv-label">Achievements via</span>
              <span class="kv-value">{{
                game.achievementsProvider === "retroachievements"
                  ? "RetroAchievements"
                  : "Native"
              }}</span>
            </div>
            <div
              v-if="
                game.ownership.format ||
                game.ownership.purchaseDate ||
                game.ownership.price !== null
              "
              class="kv-row stack"
            >
              <span class="kv-label">Ownership</span>
              <span class="kv-value ownership-info">
                <span v-if="game.ownership.format" class="ownership-format">{{
                  game.ownership.format
                }}</span>
                <span v-if="game.ownership.purchaseDate">
                  Purchased
                  {{ formatDisplayDate(game.ownership.purchaseDate) }}
                </span>
                <span v-if="game.ownership.price !== null">
                  {{ game.ownership.priceCurrency ?? "USD" }}
                  {{ game.ownership.price.toFixed(2) }}
                </span>
                <span v-if="game.ownership.condition">{{
                  game.ownership.condition
                }}</span>
              </span>
            </div>
            <div v-if="game.links.length" class="kv-row stack">
              <span class="kv-label">Links</span>
              <ul class="links-list">
                <li v-for="link in game.links" :key="link.url">
                  <a
                    :href="link.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    >{{ link.label }}</a
                  >
                </li>
              </ul>
            </div>
            <div v-if="game.folderLocation" class="kv-row stack">
              <span class="kv-label">Folder</span>
              <span class="kv-value folder-value">{{
                game.folderLocation
              }}</span>
            </div>
          </div>
        </div>
      </details>
    </section>

    <section v-else-if="activeTab === 'Achievements'" class="achievements">
      <div class="ach-head">
        <h2 class="ach-title">Achievements</h2>
        <span class="ach-count"
          >{{ unlockedCount }} / {{ game.achievements.length }}</span
        >
        <div class="ach-tools">
          <input
            v-model="achSearch"
            type="text"
            class="ui-field ach-search"
            placeholder="Search achievements…"
            aria-label="Search achievements"
          />
          <select
            v-if="achProviders.length > 1"
            v-model="achProvider"
            class="ui-field ach-sort"
            aria-label="Filter by platform"
          >
            <option value="all">All platforms</option>
            <option v-for="pr in achProviders" :key="pr" :value="pr">
              {{ pr }}
            </option>
          </select>
          <select
            v-model="mobileSort"
            class="ui-field ach-sort ach-mobile-sort"
            aria-label="Sort achievements"
          >
            <option value="recent">Recently unlocked</option>
            <option value="rarest">Rarest first</option>
            <option value="easiest">Easiest first</option>
            <option value="name">A to Z</option>
          </select>
          <button
            type="button"
            class="ui-btn ui-btn-secondary ui-btn-sm"
            :class="{ on: overallOpen || !!achLocal.overall }"
            @click="toggleOverall"
          >
            Overall notes
          </button>
        </div>
      </div>

      <div v-if="overallOpen" class="ach-overall">
        <textarea
          v-model="overallDraft"
          class="ach-textarea"
          rows="3"
          placeholder="Plans, routes and reminders for hunting this game"
          aria-label="Overall achievement notes"
        ></textarea>
        <div class="ach-note-actions">
          <button
            type="button"
            class="ui-btn ui-btn-primary ui-btn-sm"
            @click="saveOverall"
          >
            Save
          </button>
          <button
            type="button"
            class="ui-btn ui-btn-ghost ui-btn-sm"
            @click="overallOpen = false"
          >
            Cancel
          </button>
          <span class="ach-hint">Only you can see this</span>
        </div>
      </div>

      <div v-if="achStats.length" class="ach-stats">
        <span v-for="st in achStats" :key="st.label"
          ><b>{{ st.value }}</b> {{ st.label }}</span
        >
      </div>

      <SegmentedTabs
        v-if="game.achievements.length"
        :options="achFilterOptions"
        :model-value="achFilter"
        aria-label="Filter achievements"
        @update:model-value="achFilter = $event as AchFilter"
      />

      <p v-if="!game.achievements.length" class="ach-empty">
        No achievements yet. They appear here after a library sync for Steam,
        PlayStation or RetroAchievements.
      </p>
      <p v-else-if="!shownAchievements.length" class="ach-empty">
        Nothing matches that search or filter.
      </p>

      <div
        v-if="game.achievements.length && shownAchievements.length"
        class="ach-cols"
        role="row"
      >
        <span></span>
        <button
          type="button"
          class="ach-colbtn left"
          :aria-sort="ariaSort('name')"
          @click="sortBy('name')"
        >
          Achievement <i>{{ sortMark("name") }}</i>
        </button>
        <button
          type="button"
          class="ach-colbtn"
          :aria-sort="ariaSort('rarity')"
          @click="sortBy('rarity')"
        >
          <i>{{ sortMark("rarity") }}</i> Players
        </button>
        <button
          type="button"
          class="ach-colbtn"
          :aria-sort="ariaSort('unlocked')"
          @click="sortBy('unlocked')"
        >
          <i>{{ sortMark("unlocked") }}</i> Unlocked
        </button>
        <span></span>
      </div>
      <ul v-if="shownAchievements.length" class="ach-list">
        <li v-for="a in shownAchievements" :key="a.id" class="ach-item">
          <div
            class="ach-row"
            :class="{
              done: isUnlocked(a),
              lock: !isUnlocked(a),
              pin: isPinned(a),
            }"
          >
            <div
              class="ach-icon"
              :style="
                a.iconUrl && !isHiddenLocked(a)
                  ? { backgroundImage: `url(${a.iconUrl})` }
                  : {}
              "
            ></div>

            <div class="ach-main">
              <div class="ach-name">
                <span v-if="isHiddenLocked(a)" class="ach-hidden-name"
                  >Hidden achievement</span
                >
                <router-link
                  v-else
                  :to="{
                    name: 'achievement-detail',
                    params: { gameId: game.id, achievementId: a.id },
                  }"
                  class="ach-link"
                  >{{ a.name }}</router-link
                >
                <span
                  v-if="a.kind && !isHiddenLocked(a)"
                  class="ach-tag"
                  :class="a.kind"
                  >{{ KIND_LABEL[a.kind] }}</span
                >
              </div>
              <div class="ach-desc">
                <template v-if="isHiddenLocked(a)">
                  Details for this achievement will be revealed once unlocked.
                  <button
                    type="button"
                    class="ach-reveal"
                    @click="revealAchievement(a)"
                  >
                    Show
                  </button>
                </template>
                <template v-else>
                  {{ descriptionOf(a) }}
                  <button
                    v-if="a.hidden && !isUnlocked(a)"
                    type="button"
                    class="ach-reveal"
                    @click="hideAchievement(a)"
                  >
                    Hide
                  </button>
                </template>
              </div>
            </div>

            <div class="ach-col">
              <template v-if="a.rarityPercent != null">
                <div class="ach-big">{{ formatPercent(a.rarityPercent) }}</div>
                <div class="ach-lab">of players</div>
              </template>
              <div v-else class="ach-big ach-dim">–</div>
            </div>

            <div class="ach-col">
              <template v-if="isUnlocked(a)">
                <template v-if="a.unlockedAt">
                  <div class="ach-big ach-small">
                    {{ unlockedOn(a.unlockedAt).date }}
                  </div>
                  <div class="ach-lab">{{ unlockedOn(a.unlockedAt).time }}</div>
                </template>
                <div v-else class="ach-big ach-small">Unlocked</div>
              </template>
              <template
                v-else-if="a.progressCurrent != null && a.progressTarget"
              >
                <div class="ach-big ach-small">
                  {{ a.progressCurrent }} / {{ a.progressTarget }}
                </div>
                <div class="ach-bar">
                  <i
                    :style="{
                      width: `${Math.min(100, (a.progressCurrent / a.progressTarget) * 100)}%`,
                    }"
                  ></i>
                </div>
              </template>
              <div v-else class="ach-big ach-small ach-dim">Locked</div>
            </div>

            <div class="ach-acts">
              <button
                type="button"
                class="ach-btn"
                :class="{ on: isPinned(a) }"
                :aria-pressed="isPinned(a)"
                @click="togglePin(a)"
              >
                {{ isPinned(a) ? "Pinned" : "Pin" }}
              </button>
              <button
                type="button"
                class="ach-btn"
                :class="{ on: !!achLocal.notes[a.id] || noteOpen === a.id }"
                @click="toggleNote(a)"
              >
                {{ achLocal.notes[a.id] ? "Note · 1" : "Note" }}
              </button>
              <button
                v-if="mediaByAchievement.get(a.id)?.length"
                type="button"
                class="ach-btn ach-btn-media"
                :class="{ on: achMediaOpen === a.id }"
                :title="`${mediaByAchievement.get(a.id)!.length} tied to this achievement`"
                @click="toggleAchMedia(a)"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <rect x="3" y="4" width="18" height="16" rx="2" />
                  <circle cx="9" cy="10" r="1.6" />
                  <path d="M21 16l-5-5-8 9" />
                </svg>
                {{ mediaByAchievement.get(a.id)!.length }}
              </button>
            </div>
          </div>

          <div v-if="achMediaOpen === a.id" class="ach-media-strip">
            <template v-for="m in mediaByAchievement.get(a.id)" :key="m.id">
              <button
                v-if="m.kind === 'screenshot'"
                type="button"
                class="ach-media-thumb"
                :title="m.note ?? 'View screenshot'"
                @click="lightboxUrl = m.url"
              >
                <img :src="m.url" alt="" loading="lazy" />
              </button>
              <video
                v-else-if="m.kind === 'clip'"
                class="ach-media-thumb"
                :src="m.url"
                controls
                preload="metadata"
              ></video>
              <audio
                v-else
                class="ach-media-audio"
                :src="m.url"
                controls
                preload="metadata"
              ></audio>
            </template>
          </div>

          <div v-if="noteOpen === a.id" class="ach-note-box">
            <textarea
              v-model="noteDraft"
              class="ach-textarea"
              rows="2"
              placeholder="How you got it, or how you plan to"
              :aria-label="`Note on ${a.name}`"
            ></textarea>
            <div class="ach-note-actions">
              <button
                type="button"
                class="ui-btn ui-btn-primary ui-btn-sm"
                @click="saveNote(a)"
              >
                Save
              </button>
              <button
                type="button"
                class="ui-btn ui-btn-ghost ui-btn-sm"
                @click="noteOpen = null"
              >
                Cancel
              </button>
              <button
                v-if="achLocal.notes[a.id]"
                type="button"
                class="ui-btn ui-btn-ghost ui-btn-sm"
                @click="clearNote(a)"
              >
                Delete note
              </button>
            </div>
          </div>
        </li>
      </ul>
      <div
        v-if="lightboxUrl"
        class="lightbox-backdrop"
        @click="lightboxUrl = null"
      >
        <img :src="lightboxUrl" alt="" class="lightbox-image" />
      </div>
    </section>

    <section v-else-if="activeTab === 'Notes'" class="notes-panel">
      <GameNotesPanel
        :game-id="game.id"
        :achievements="tieAchievements"
        :open-note="(route.query.note as string | undefined) ?? null"
        @open-achievement="openAchievement"
      />
    </section>

    <GameAccountsPanel v-else-if="activeTab === 'Accounts'" />

    <section
      v-else-if="
        activeTab === 'Screenshots' ||
        activeTab === 'Clips' ||
        activeTab === 'Soundtrack'
      "
      class="media-panel"
    >
      <GameMediaPanel
        :kind="
          activeTab === 'Screenshots'
            ? 'screenshot'
            : activeTab === 'Clips'
              ? 'clip'
              : 'soundtrack'
        "
        :items="
          activeTab === 'Screenshots'
            ? screenshots
            : activeTab === 'Clips'
              ? clips
              : soundtrackItems
        "
        :trash="activeTabTrash"
        :achievements="tieAchievements"
        :profiles="game.profilesEnabled ? profiles : undefined"
        :loading="mediaLoadedFor !== game.id && !mediaError"
        :uploading="uploadingMedia"
        :error="mediaError"
        @files="onMediaFilesSelected"
        @delete="removeMedia"
        :detect="detectOne"
        @save="saveMediaItem"
        @bulk-save="bulkSaveMedia"
        @bulk-delete="bulkDeleteMedia"
        @bulk-detect="detectMany"
        @restore="restoreMediaItem"
        @open-achievement="openAchievement"
        @thumbnail="keepThumbnail"
        @problem="mediaError = $event"
      />
    </section>

    <section v-else-if="activeTab === 'Saves'" class="files-panel">
      <GameArchivesPanel
        title="Saves"
        plural="saves"
        singular="save"
        hint="Drop a save here or click to browse. You'll be asked to name it: one game can hold as many named saves as you want."
        :archives="saveArchives"
        :trash="saveTrash"
        :loaded="saveArchivesLoaded"
        :uploading="saveUploading.has('')"
        :error="filesError"
        @files="onNewSaveSelected"
        @bulk-delete="bulkDeleteArchives($event, false)"
        @restore="onRestoreArchive($event, false)"
        @problem="filesError = $event"
      >
        <template #card="{ archive, selecting, selected, toggle }">
          <ArchiveCard
            :archive="archive"
            kind="save"
            :selecting="selecting"
            :selected="selected"
            :uploading="saveUploading.has(archive.id)"
            @toggle="toggle"
            @edit="openArchiveEdit($event, false)"
            @delete="onDeleteArchive($event, false)"
            @add-version="onAddSaveVersion"
          />
        </template>
      </GameArchivesPanel>
    </section>

    <section v-else-if="activeTab === 'Docs'" class="files-panel">
      <PluginExtensionSlot
        slot-id="game.documents.after-header"
        :context="{ host_page: 'game.documents', game_id: game.id }"
      />
      <PluginContextualActions
        :context="{ kind: 'game', resource_id: game.id }"
      />
      <GameMediaPanel
        kind="doc"
        :game-id="game.id"
        :items="docsFiles"
        :trash="docsTrash"
        :loading="filesLoaded.doc === null"
        :uploading="uploadingFiles"
        :error="filesError"
        @files="onGameFilesSelected($event, 'doc')"
        @delete="removeGameFile('doc', $event)"
        @save="(item, patch) => saveGameFile('doc', item, patch)"
        @bulk-save="bulkSaveFiles('doc', $event)"
        @bulk-delete="(items) => items.forEach((f) => removeGameFile('doc', f))"
        @restore="restoreFileItem('doc', $event as TrashedGameFile)"
        @problem="filesError = $event"
      />
    </section>

    <GameWorldMapPanel v-else-if="activeTab === 'World Map'" />

    <section v-else-if="activeTab === 'Stats'" class="stats-panel">
      <GameStatsPanel
        :show-achievements="achievementsOn"
        :show-rating="!pageSettings.hide_rating"
        :hide-history="pageSettings.hide_history"
        :game="game"
        :changes="fieldChanges"
        :media="mediaItems"
        :loading="fieldChangesLoading"
        :error="fieldChangesError"
      />
    </section>
  </main>

  <main v-else class="not-found">
    <p>Game not found.</p>
  </main>
</template>
<style src="../styles/pages/game-detail-layout.css" />
<style src="../styles/pages/game-detail-media.css" />
