<script setup lang="ts">
import PluginExtensionSlot from "../components/plugins/PluginExtensionSlot.vue";
import PluginContextualActions from "../components/plugins/PluginContextualActions.vue";
import UploadDropzone from "../components/UploadDropzone.vue";
import ViewUploadSidebar from "../components/ViewUploadSidebar.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import MediaTile from "../components/MediaTile.vue";
import GameFormModal from "../components/GameFormModal.vue";
import CollectionPickerModal from "../components/CollectionPickerModal.vue";
import BackButton from "../components/BackButton.vue";
import AccountChip from "../components/AccountChip.vue";
import GameAccountsPanel from "../components/game/GameAccountsPanel.vue";
import GameWorldMapPanel from "../components/game/GameWorldMapPanel.vue";
import { provide } from "vue";
import { useGameDetail } from "../composables/useGameDetail";
import { gameDetailKey } from "../composables/gameDetailContext";
const model = useGameDetail();
provide(gameDetailKey, model);
const {
  documentReaderUrl,
  formatDisplayDate,
  activePriority,
  priorityLabel,
  goBackToLibrary,
  game,
  loading,
  error,
  showEditModal,
  deleting,
  deleteError,
  showDeleteConfirm,
  noteNames,
  noteMode,
  viewingNoteName,
  editingNoteName,
  draftName,
  draftContent,
  noteLoading,
  noteSaving,
  noteError,
  hasDraft,
  renderedNoteHtml,
  startNewNote,
  viewNote,
  editFromView,
  backToList,
  saveDraft,
  deleteNote,
  descriptionHtml,
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
  showCollectionPicker,
  onCollectionAdded,
  onDeleteFromModal,
  confirmDelete,
  recentActivity,
  tally,
  statsPlaytimeLabel,
  unlockedAchievements,
  firstUnlockedAt,
  lastUnlockedAt,
  formatStatsDate,
  activeTab,
  visibleTabs,
  panelMode,
  onDropError,
  onPreviewMedia,
  mediaLoading,
  mediaError,
  screenshots,
  clips,
  soundtrackItems,
  lightboxUrl,
  uploadingMedia,
  onMediaFilesSelected,
  removeMedia,
  showMediaTrash,
  activeTabTrash,
  restoreMediaItem,
  saveMediaItem,
  docsFiles,
  filesError,
  uploadingFiles,
  fieldChanges,
  fieldChangesLoading,
  fieldChangesError,
  FIELD_CHANGE_LABELS,
  formatFieldChangeDate,
  onGameFilesSelected,
  removeGameFile,
  docsTrash,
  showDocsTrash,
  restoreFileItem,
  formatFileSize,
  formatArchiveDate,
  saveArchives,
  saveArchivesLoaded,
  expandedSaveId,
  saveUploading,
  onNewSaveSelected,
  onAddSaveVersion,
  onRenameArchive,
  onDeleteArchive,
  saveTrash,
  showSaveTrash,
  daysUntil,
  onRestoreArchive,
  onDeleteVersion,
  displayFileName,
  sortedAchievements,
  deriveTier,
  isPlatinumEarned,
  trophyCounts,
  formatUnlockedAt,
  formatPlaytime,
} = model;
</script>
<template>
  <main v-if="loading" class="game-detail-page detail loading-state">
    <div class="detail-skeleton">
      <SkeletonBlock height="320px" radius="0" />
      <div class="detail-skeleton-body">
        <SkeletonBlock width="45%" height="28px" />
        <div class="detail-skeleton-pills">
          <SkeletonBlock width="80px" height="24px" radius="999px" />
          <SkeletonBlock width="100px" height="24px" radius="999px" />
          <SkeletonBlock width="70px" height="24px" radius="999px" />
        </div>
        <div class="detail-skeleton-tabs">
          <SkeletonBlock
            v-for="i in 6"
            :key="i"
            width="70px"
            height="30px"
            radius="8px"
          />
        </div>
        <SkeletonBlock height="140px" />
      </div>
    </div>
  </main>

  <main v-else-if="error" class="game-detail-page detail error-state">
    <p>{{ error }}</p>
  </main>

  <main v-else-if="game" class="game-detail-page detail">
    <!-- heavily blurred, dimmed copy of the cover image behind the whole page,
         separate from the sharp version used in .hero itself -->
    <div
      class="ambient-bg"
      :style="{ backgroundImage: `url(${game.bannerImageUrl})` }"
    ></div>

    <BackButton fixed @click="goBackToLibrary" />

    <AccountChip fixed />

    <GameFormModal
      v-if="showEditModal"
      :game="game"
      @close="showEditModal = false"
      @saved="onGameSaved"
      @delete="onDeleteFromModal"
    />

    <CollectionPickerModal
      v-if="showCollectionPicker"
      :game="game"
      @close="showCollectionPicker = false"
      @added="onCollectionAdded"
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

    <section
      class="hero"
      :style="{ backgroundImage: `url(${game.bannerImageUrl})` }"
    >
      <div class="hero-overlay"></div>
      <div class="hero-actions">
        <button
          class="hero-icon-button"
          type="button"
          title="Add to collection"
          @click="showCollectionPicker = true"
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
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
          </svg>
        </button>
        <button
          class="hero-icon-button"
          :class="{ active: game.favorite }"
          type="button"
          :title="game.favorite ? 'Remove from favorites' : 'Add to favorites'"
          @click="toggleFavorite"
        >
          <svg
            viewBox="0 0 24 24"
            width="16"
            height="16"
            :fill="game.favorite ? 'currentColor' : 'none'"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.6z"
            />
          </svg>
        </button>
        <button class="edit-button" type="button" @click="showEditModal = true">
          Edit
        </button>
      </div>
      <div class="hero-inner">
        <router-link
          v-if="game.parentGameId"
          :to="`/games/${game.parentGameId}`"
          class="parent-breadcrumb"
        >
          {{ parentGameTitle ?? "…" }}
          <span v-if="game.relationshipType" class="relationship-tag">{{
            RELATIONSHIP_LABELS[game.relationshipType] ?? game.relationshipType
          }}</span>
          →
        </router-link>
        <h1>{{ game.title }}</h1>
        <div class="badges">
          <span class="badge status-badge">{{ game.status }}</span>
          <span v-if="tally" class="badge rating-badge">
            ★ {{ tally.sum.toFixed(1) }}
          </span>
          <span v-if="game.dateAdded" class="badge">
            {{ new Date(game.dateAdded).toLocaleDateString() }}
          </span>
          <span v-if="game.platforms.length" class="badge">{{
            game.platforms[0].platform
          }}</span>
          <button
            v-if="game.achievementTotal > 0"
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
      </div>
    </section>

    <nav class="tabs">
      <button
        v-for="tab in visibleTabs"
        :key="tab"
        type="button"
        class="tab"
        :class="{ active: activeTab === tab }"
        @click="activeTab = tab"
      >
        {{ tab }}
      </button>
    </nav>

    <PluginExtensionSlot
      v-if="activeTab === 'Overview'"
      slot-id="game.overview.after-header"
      :context="{ host_page: 'game.overview', game_id: game.id }"
    />
    <PluginContextualActions
      :context="{ kind: 'game', resource_id: game.id }"
    />

    <section v-if="activeTab === 'Overview'" class="overview">
      <div class="overview-main">
        <div class="resume-note-card">
          <div class="resume-note-header">
            <h3>Where I left off</h3>
            <button
              v-if="!resumeNoteEditing"
              type="button"
              class="text-button"
              @click="startEditResumeNote"
            >
              {{ game.resumeNote ? "Edit" : "+ Add note" }}
            </button>
          </div>
          <template v-if="resumeNoteEditing">
            <textarea
              v-model="resumeNoteDraft"
              class="resume-note-textarea"
              rows="3"
              placeholder="e.g. Just beat the third boss, about to start the desert region…"
            ></textarea>
            <div v-if="resumeNoteError" class="form-error-inline">
              {{ resumeNoteError }}
            </div>
            <div class="resume-note-actions">
              <button
                type="button"
                class="secondary-button"
                @click="resumeNoteEditing = false"
              >
                Cancel
              </button>
              <button
                type="button"
                class="primary-button"
                :disabled="resumeNoteSaving"
                @click="saveResumeNote"
              >
                {{ resumeNoteSaving ? "Saving…" : "Save" }}
              </button>
            </div>
          </template>
          <p v-else-if="game.resumeNote" class="resume-note-text">
            {{ game.resumeNote }}
          </p>
          <p v-else class="resume-note-empty">
            Nothing noted yet. Jot down what to do next time you pick this up.
          </p>
        </div>

        <div v-if="descriptionHtml" class="description-wrap">
          <div class="description-html" v-html="descriptionHtml"></div>
        </div>

        <div v-if="variants.length" class="variants-section">
          <h3 class="variants-heading">Variants</h3>
          <div class="variants-row">
            <router-link
              v-for="variant in variants"
              :key="variant.id"
              :to="`/games/${variant.id}`"
              class="variant-card"
            >
              <img :src="variant.coverImageUrl" alt="" class="variant-cover" />
              <span class="variant-title">{{ variant.title }}</span>
              <span v-if="variant.relationshipType" class="relationship-tag">
                {{
                  RELATIONSHIP_LABELS[variant.relationshipType] ??
                  variant.relationshipType
                }}
              </span>
            </router-link>
          </div>
        </div>

        <div v-if="similarGames.length" class="similar-games-section">
          <h3 class="variants-heading">Similar games in your library</h3>
          <div class="variants-row">
            <router-link
              v-for="g in similarGames"
              :key="g.id"
              :to="`/games/${g.id}`"
              class="variant-card"
            >
              <img :src="g.coverImageUrl" alt="" class="variant-cover" />
              <span class="variant-title">{{ g.title }}</span>
            </router-link>
          </div>
        </div>

        <div
          class="rating-breakdown"
          v-if="
            game.ratingOverall !== null ||
            game.ratingStory !== null ||
            game.ratingGameplay !== null ||
            game.ratingSound !== null
          "
        >
          <div v-if="game.ratingOverall !== null" class="rating-item">
            <span class="rating-label">Atmosphere</span>
            <span class="rating-score"
              >★ {{ game.ratingOverall.toFixed(1) }}</span
            >
          </div>
          <div v-if="game.ratingStory !== null" class="rating-item">
            <span class="rating-label">Story</span>
            <span class="rating-score"
              >★ {{ game.ratingStory.toFixed(1) }}</span
            >
          </div>
          <div v-if="game.ratingGameplay !== null" class="rating-item">
            <span class="rating-label">Gameplay</span>
            <span class="rating-score"
              >★ {{ game.ratingGameplay.toFixed(1) }}</span
            >
          </div>
          <div v-if="game.ratingSound !== null" class="rating-item">
            <span class="rating-label">Sound</span>
            <span class="rating-score"
              >★ {{ game.ratingSound.toFixed(1) }}</span
            >
          </div>
          <div v-if="tally" class="rating-item">
            <span class="rating-label">Score</span>
            <span class="rating-score">{{ tally.sum.toFixed(1) }}</span>
          </div>
        </div>
      </div>

      <aside class="details-panel">
        <h3 class="panel-title">Details</h3>
        <div class="detail-row">
          <span class="detail-label">Developer</span>
          <span class="detail-value">{{ game.developer ?? "N/A" }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Publisher</span>
          <span class="detail-value">{{ game.publisher ?? "N/A" }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Series</span>
          <span class="detail-value">{{ game.series ?? "N/A" }}</span>
        </div>
        <div v-if="game.releaseDate" class="detail-row">
          <span class="detail-label">Release Date</span>
          <span class="detail-value">{{
            formatDisplayDate(game.releaseDate)
          }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Date Added</span>
          <span class="detail-value">
            {{
              game.dateAdded
                ? new Date(game.dateAdded).toLocaleDateString()
                : "N/A"
            }}
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Recent Activity</span>
          <span class="detail-value">
            {{
              recentActivity
                ? new Date(recentActivity).toLocaleDateString()
                : "N/A"
            }}
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Platforms</span>
          <ul class="platforms">
            <li
              v-for="p in game.platforms"
              :key="p.platform"
              class="platform-row"
            >
              <div class="platform-line">
                <span class="platform-name">{{ p.platform }}</span>
                <span class="platform-meta">
                  {{ formatPlaytime(p.playtimeMinutes)
                  }}<span v-if="p.completionPercent !== null">
                    · {{ p.completionPercent }}%</span
                  >
                </span>
              </div>
              <div v-if="p.lastPlayedAt" class="platform-last-played">
                last played {{ new Date(p.lastPlayedAt).toLocaleDateString() }}
              </div>
            </li>
          </ul>
          <button
            type="button"
            class="text-button log-playtime-button"
            :disabled="loggingPlaytime"
            title="Log a session just played, without editing the total by hand"
            @click="logPlaytime(30)"
          >
            + Log 30 min just played
          </button>
        </div>
        <div v-if="game.tags.length" class="detail-row">
          <span class="detail-label">Tags</span>
          <span class="feature-pills">
            <span v-for="tag in game.tags" :key="tag" class="feature-pill">{{
              tag
            }}</span>
          </span>
        </div>
        <div v-if="game.features.length" class="detail-row">
          <span class="detail-label">Features</span>
          <span class="feature-pills">
            <span v-for="f in game.features" :key="f" class="feature-pill">{{
              f
            }}</span>
          </span>
        </div>
        <div v-if="game.source" class="detail-row">
          <span class="detail-label">Source</span>
          <span class="detail-value">{{ game.source }}</span>
        </div>
        <div v-if="activePriority(game) !== null" class="detail-row">
          <span class="detail-label">Priority</span>
          <span class="detail-value">{{
            priorityLabel(activePriority(game)!)
          }}</span>
        </div>
        <div v-if="game.ageRating" class="detail-row">
          <span class="detail-label">Age Rating</span>
          <span class="detail-value">{{ game.ageRating }}</span>
        </div>
        <div v-if="game.timeToBeatHours" class="detail-row">
          <span class="detail-label">Time to Beat</span>
          <span class="detail-value">{{ game.timeToBeatHours }}h</span>
        </div>
        <div v-if="game.region" class="detail-row">
          <span class="detail-label">Region</span>
          <span class="detail-value">{{ game.region }}</span>
        </div>
        <div v-if="game.language" class="detail-row">
          <span class="detail-label">Language</span>
          <span class="detail-value">{{ game.language }}</span>
        </div>
        <div v-if="game.achievementsProvider" class="detail-row">
          <span class="detail-label">Achievement Tracking</span>
          <span class="detail-value">{{
            game.achievementsProvider === "retroachievements"
              ? "RetroAchievements"
              : "Native"
          }}</span>
        </div>
        <div v-if="game.links.length" class="detail-row">
          <span class="detail-label">Links</span>
          <ul class="links-list">
            <li v-for="link in game.links" :key="link.url">
              <a :href="link.url" target="_blank" rel="noopener noreferrer">{{
                link.label
              }}</a>
            </li>
          </ul>
        </div>
        <div
          v-if="
            game.ownership.format ||
            game.ownership.purchaseDate ||
            game.ownership.price !== null
          "
          class="detail-row"
        >
          <span class="detail-label">Ownership</span>
          <div class="ownership-info">
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
          </div>
        </div>
        <div v-if="game.folderLocation" class="detail-row">
          <span class="detail-label">Folder</span>
          <span class="detail-value">{{ game.folderLocation }}</span>
        </div>
      </aside>
    </section>

    <section v-else-if="activeTab === 'Achievements'" class="achievements">
      <div class="achievements-header">
        <h2>Achievements</h2>
        <span class="percent">{{ game.achievementPercent }}%</span>
      </div>

      <div class="trophy-summary">
        <div class="trophy-count">
          <span
            class="trophy-badge trophy-badge-platinum"
            :class="{ dim: !isPlatinumEarned }"
          ></span>
          <span>{{ isPlatinumEarned ? 1 : 0 }}</span>
        </div>
        <div class="trophy-count">
          <span class="trophy-badge trophy-badge-gold"></span>
          <span>{{ trophyCounts.gold }}</span>
        </div>
        <div class="trophy-count">
          <span class="trophy-badge trophy-badge-silver"></span>
          <span>{{ trophyCounts.silver }}</span>
        </div>
        <div class="trophy-count">
          <span class="trophy-badge trophy-badge-bronze"></span>
          <span>{{ trophyCounts.bronze }}</span>
        </div>
      </div>

      <ul class="achievement-list">
        <li
          v-for="achievement in sortedAchievements(game.achievements)"
          :key="achievement.id"
        >
          <router-link
            :to="{
              name: 'achievement-detail',
              params: { gameId: game.id, achievementId: achievement.id },
            }"
            class="achievement-row"
            :class="{ unlocked: achievement.unlockedAt !== null }"
          >
            <div
              class="achievement-icon"
              :style="
                achievement.hidden && achievement.unlockedAt === null
                  ? {}
                  : { backgroundImage: `url(${game.coverImageUrl})` }
              "
            >
              <span
                class="achievement-badge"
                :class="
                  achievement.unlockedAt !== null
                    ? `badge-${deriveTier(achievement)}`
                    : 'badge-locked'
                "
              >
                <template
                  v-if="achievement.hidden && achievement.unlockedAt === null"
                  >?</template
                >
              </span>
            </div>

            <div class="achievement-info">
              <template
                v-if="achievement.hidden && achievement.unlockedAt === null"
              >
                <span class="achievement-name">Hidden Trophy</span>
                <span class="achievement-description"
                  >Unlock this achievement to reveal it.</span
                >
              </template>
              <template v-else>
                <span class="achievement-name">{{ achievement.name }}</span>
                <span
                  v-if="achievement.description"
                  class="achievement-description"
                  >{{ achievement.description }}</span
                >
              </template>

              <div
                v-if="achievement.unlockedAt !== null"
                class="achievement-unlocked-at"
              >
                Unlocked {{ formatUnlockedAt(achievement.unlockedAt) }}
              </div>
              <div
                v-else-if="
                  achievement.progressCurrent != null &&
                  achievement.progressTarget
                "
                class="achievement-progress"
              >
                <div class="progress-bar">
                  <div
                    class="progress-fill"
                    :style="{
                      width: `${Math.min(100, (achievement.progressCurrent / achievement.progressTarget) * 100)}%`,
                    }"
                  ></div>
                </div>
                <span class="progress-label"
                  >{{ achievement.progressCurrent }} /
                  {{ achievement.progressTarget }}</span
                >
              </div>
            </div>
          </router-link>
        </li>
      </ul>
    </section>

    <section v-else-if="activeTab === 'Notes'" class="notes-panel">
      <div v-if="noteMode === 'list'" class="notes-list-view">
        <div class="notes-header-row">
          <h2>Notes</h2>
          <button type="button" class="primary-button" @click="startNewNote">
            {{ hasDraft ? "Continue Draft" : "New Note" }}
          </button>
        </div>

        <div v-if="noteError" class="note-error">{{ noteError }}</div>

        <p v-if="noteLoading" class="empty-state">Loading…</p>
        <p v-else-if="!noteNames.length" class="empty-state">No notes yet.</p>
        <ul v-else class="notes-list">
          <li
            v-for="note in noteNames"
            :key="note"
            class="notes-list-row"
            @click="void viewNote(note)"
          >
            <span class="note-name">{{ note }}</span>
            <div class="notes-list-actions">
              <button
                type="button"
                class="danger-button"
                :disabled="noteSaving"
                @click.stop="void deleteNote(note)"
              >
                Delete
              </button>
            </div>
          </li>
        </ul>
      </div>

      <div v-else-if="noteMode === 'view'" class="notes-editor">
        <div class="notes-editor-card">
          <div class="notes-toolbar">
            <button type="button" class="small-button" @click="backToList">
              ← Back
            </button>
            <span class="selected-note">{{ viewingNoteName }}</span>
            <button type="button" class="small-button" @click="editFromView">
              Edit
            </button>
          </div>

          <div v-if="noteLoading" class="empty-state">Loading…</div>
          <div v-else class="note-rendered" v-html="renderedNoteHtml"></div>

          <div v-if="noteError" class="note-error">{{ noteError }}</div>
        </div>
      </div>

      <div v-else class="notes-editor">
        <div class="notes-editor-card">
          <div class="notes-toolbar">
            <button type="button" class="small-button" @click="backToList">
              ← Back
            </button>
          </div>

          <label class="field">
            <span>Note name</span>
            <input
              v-model="draftName"
              type="text"
              placeholder="Meeting notes"
              autocomplete="off"
            />
          </label>

          <textarea
            v-model="draftContent"
            placeholder="Write markdown here…"
            spellcheck="true"
          ></textarea>

          <div v-if="noteError" class="note-error">{{ noteError }}</div>

          <div class="notes-editor-actions">
            <button type="button" class="small-button" @click="backToList">
              Cancel
            </button>
            <button
              type="button"
              class="primary-button"
              :disabled="noteSaving || !draftName.trim()"
              @click="void saveDraft()"
            >
              {{
                noteSaving
                  ? "Saving…"
                  : editingNoteName
                    ? "Save changes"
                    : "Create note"
              }}
            </button>
          </div>
        </div>
      </div>
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
      <h2>{{ activeTab }}</h2>
      <div class="panel-body">
        <ViewUploadSidebar v-model="panelMode" />
        <div class="panel-content">
          <template v-if="panelMode === 'upload'">
            <UploadDropzone
              :accept="
                activeTab === 'Screenshots'
                  ? 'image/*'
                  : activeTab === 'Clips'
                    ? 'video/*'
                    : 'audio/*'
              "
              :uploading="uploadingMedia"
              :title="`Drop ${activeTab.toLowerCase()} here`"
              :hint="`Drag and drop ${activeTab === 'Soundtrack' ? 'audio' : activeTab.toLowerCase()}, or click to browse`"
              @files-selected="onMediaFilesSelected"
              @drop-error="onDropError"
            />
            <div v-if="mediaError" class="form-error">{{ mediaError }}</div>
          </template>

          <template v-else>
            <p v-if="mediaLoading">Loading…</p>
            <p
              v-else-if="
                (activeTab === 'Screenshots' && !screenshots.length) ||
                (activeTab === 'Clips' && !clips.length) ||
                (activeTab === 'Soundtrack' && !soundtrackItems.length)
              "
              class="empty-row"
            >
              No {{ activeTab.toLowerCase() }} yet: switch to Upload to add
              some.
            </p>
            <div v-else class="media-grid">
              <MediaTile
                v-for="item in activeTab === 'Screenshots'
                  ? screenshots
                  : activeTab === 'Clips'
                    ? clips
                    : soundtrackItems"
                :key="item.id"
                :item="item"
                :achievements="game.achievements"
                :profiles="game.profilesEnabled ? profiles : undefined"
                @preview="onPreviewMedia($event.url)"
                @delete="removeMedia"
                @save="saveMediaItem"
              />
            </div>

            <div v-if="activeTabTrash.length" class="trash-section">
              <button
                type="button"
                class="trash-toggle"
                @click="showMediaTrash = !showMediaTrash"
              >
                {{ showMediaTrash ? "▾" : "▸" }} Recently deleted ({{
                  activeTabTrash.length
                }})
              </button>
              <ul v-if="showMediaTrash" class="trash-list">
                <li
                  v-for="item in activeTabTrash"
                  :key="item.id"
                  class="trash-row"
                >
                  <span class="trash-name">{{
                    item.filename.split("_").slice(1).join("_")
                  }}</span>
                  <span class="trash-meta"
                    >purges in {{ daysUntil(item.purge_at) }}d</span
                  >
                  <button
                    type="button"
                    class="secondary-button small"
                    @click="restoreMediaItem(item)"
                  >
                    Restore
                  </button>
                </li>
              </ul>
            </div>
          </template>
        </div>
      </div>
      <div
        v-if="lightboxUrl"
        class="lightbox-backdrop"
        @click="lightboxUrl = null"
      >
        <img :src="lightboxUrl" alt="" class="lightbox-image" />
      </div>
    </section>

    <section v-else-if="activeTab === 'Saves'" class="files-panel">
      <h2>Saves</h2>
      <div class="panel-body">
        <ViewUploadSidebar v-model="panelMode" />
        <div class="panel-content">
          <template v-if="panelMode === 'upload'">
            <UploadDropzone
              accept="*/*"
              :uploading="saveUploading.has('')"
              title="Drop a new save here"
              hint="You'll be asked to name it: one game can hold as many named saves as you want"
              @files-selected="onNewSaveSelected"
              @drop-error="onDropError"
            />
            <div v-if="filesError" class="form-error">{{ filesError }}</div>
          </template>

          <template v-else>
            <p
              v-if="!saveArchives.length && saveArchivesLoaded"
              class="empty-row"
            >
              No saves yet: switch to Upload to add one.
            </p>
            <div v-else class="archive-grid">
              <div
                v-for="archive in saveArchives"
                :key="archive.id"
                class="archive-card"
              >
                <div class="archive-card-header">
                  <span class="archive-name">{{ archive.name }}</span>
                  <div class="archive-card-actions">
                    <button
                      type="button"
                      class="icon-button"
                      title="Rename"
                      @click="onRenameArchive(archive, false)"
                    >
                      ✎
                    </button>
                    <button
                      type="button"
                      class="icon-button"
                      title="Delete"
                      @click="onDeleteArchive(archive, false)"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <p class="archive-meta">
                  {{ archive.versions.length }} version{{
                    archive.versions.length === 1 ? "" : "s"
                  }}
                  · latest
                  {{
                    archive.versions[0]
                      ? formatArchiveDate(archive.versions[0].uploaded_at)
                      : "N/A"
                  }}
                </p>
                <div class="archive-actions-row">
                  <a
                    v-if="archive.versions[0]"
                    :href="archive.versions[0].url"
                    class="secondary-button small"
                    >Download latest</a
                  >
                  <label class="secondary-button small upload-label">
                    {{
                      saveUploading.has(archive.id)
                        ? "Uploading…"
                        : "Add new version"
                    }}
                    <input
                      type="file"
                      class="hidden-input"
                      :disabled="saveUploading.has(archive.id)"
                      @change="
                        onAddSaveVersion(
                          archive,
                          Array.from(
                            ($event.target as HTMLInputElement).files ?? [],
                          ),
                        )
                      "
                    />
                  </label>
                  <button
                    v-if="archive.versions.length > 1"
                    type="button"
                    class="secondary-button small"
                    @click="
                      expandedSaveId =
                        expandedSaveId === archive.id ? null : archive.id
                    "
                  >
                    {{
                      expandedSaveId === archive.id ? "Hide history" : "History"
                    }}
                  </button>
                </div>
                <ul
                  v-if="expandedSaveId === archive.id"
                  class="archive-history"
                >
                  <li
                    v-for="version in archive.versions.slice(1)"
                    :key="version.id"
                    class="archive-history-row"
                  >
                    <a :href="version.url" class="file-name">{{
                      formatArchiveDate(version.uploaded_at)
                    }}</a>
                    <span class="file-size">{{
                      formatFileSize(version.size)
                    }}</span>
                    <button
                      type="button"
                      class="tile-remove-inline"
                      title="Delete this version"
                      @click="onDeleteVersion(archive, version, false)"
                    >
                      ✕
                    </button>
                  </li>
                </ul>
              </div>
            </div>
          </template>

          <div v-if="saveTrash.length" class="trash-section">
            <button
              type="button"
              class="trash-toggle"
              @click="showSaveTrash = !showSaveTrash"
            >
              {{ showSaveTrash ? "▾" : "▸" }} Recently deleted ({{
                saveTrash.length
              }})
            </button>
            <ul v-if="showSaveTrash" class="trash-list">
              <li
                v-for="archive in saveTrash"
                :key="archive.id"
                class="trash-row"
              >
                <span class="trash-name">{{ archive.name }}</span>
                <span class="trash-meta"
                  >purges in {{ daysUntil(archive.purge_at) }}d</span
                >
                <button
                  type="button"
                  class="secondary-button small"
                  @click="onRestoreArchive(archive, false)"
                >
                  Restore
                </button>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'Docs'" class="files-panel">
      <h2>Docs</h2>
      <PluginExtensionSlot
        slot-id="game.documents.actions"
        :context="{ host_page: 'game.documents', game_id: game.id }"
      />
      <PluginContextualActions
        :context="{
          kind: 'documents',
          resource_id: game.id,
          resource_type: 'game',
        }"
      />
      <div class="panel-body">
        <ViewUploadSidebar v-model="panelMode" />
        <div class="panel-content">
          <template v-if="panelMode === 'upload'">
            <UploadDropzone
              accept="*/*"
              :uploading="uploadingFiles"
              title="Drop documents here"
              hint="Any file format: drag and drop, or click to browse"
              @files-selected="onGameFilesSelected($event, 'doc')"
              @drop-error="onDropError"
            />
            <p class="section-hint">
              Manuals, walkthroughs, strategy guides: any file format.
            </p>
            <div v-if="filesError" class="form-error">{{ filesError }}</div>
          </template>

          <template v-else>
            <p v-if="!docsFiles.length" class="empty-row">
              No docs yet: switch to Upload to add one.
            </p>
            <ul v-else class="file-list">
              <li
                v-for="file in docsFiles"
                :key="file.filename"
                class="file-row"
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
                    d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                  />
                  <path d="M14 2v6h6" />
                </svg>
                <a
                  :href="documentReaderUrl(game.id, file) ?? file.url"
                  class="file-name"
                  target="_blank"
                  rel="noopener noreferrer"
                  >{{ displayFileName(file.filename) }}</a
                >
                <span class="file-size">{{ formatFileSize(file.size) }}</span>
                <a :href="file.url" download class="file-download">Download</a>
                <button
                  type="button"
                  class="tile-remove-inline"
                  title="Delete"
                  @click="removeGameFile('doc', file)"
                >
                  ✕
                </button>
              </li>
            </ul>
          </template>

          <div v-if="docsTrash.length" class="trash-section">
            <button
              type="button"
              class="trash-toggle"
              @click="showDocsTrash = !showDocsTrash"
            >
              {{ showDocsTrash ? "▾" : "▸" }} Recently deleted ({{
                docsTrash.length
              }})
            </button>
            <ul v-if="showDocsTrash" class="trash-list">
              <li
                v-for="file in docsTrash"
                :key="file.filename"
                class="trash-row"
              >
                <span class="trash-name">{{
                  displayFileName(file.filename)
                }}</span>
                <span class="trash-meta"
                  >purges in {{ daysUntil(file.purge_at) }}d</span
                >
                <button
                  type="button"
                  class="secondary-button small"
                  @click="restoreFileItem('doc', file)"
                >
                  Restore
                </button>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <GameWorldMapPanel v-else-if="activeTab === 'World Map'" />

    <section v-else-if="activeTab === 'Stats'" class="stats-panel">
      <h2>Stats</h2>
      <div class="stats-grid">
        <div class="stat-tile">
          <span class="stat-label">Total playtime</span>
          <span class="stat-value">{{ statsPlaytimeLabel }}</span>
        </div>
        <div class="stat-tile">
          <span class="stat-label">Achievements</span>
          <span class="stat-value">
            {{
              game.achievementTotal
                ? `${unlockedAchievements.length} / ${game.achievementTotal}`
                : "N/A"
            }}
          </span>
        </div>
        <div class="stat-tile">
          <span class="stat-label">Completion</span>
          <span class="stat-value">{{
            game.achievementTotal ? `${game.achievementPercent}%` : "N/A"
          }}</span>
        </div>
        <div class="stat-tile">
          <span class="stat-label">Rating</span>
          <span class="stat-value">{{
            tally ? `${tally.sum.toFixed(1)} / ${tally.max}` : "N/A"
          }}</span>
        </div>
        <div class="stat-tile">
          <span class="stat-label">Status</span>
          <span class="stat-value">{{ game.status }}</span>
        </div>
        <div class="stat-tile">
          <span class="stat-label">Source</span>
          <span class="stat-value">{{ game.source || "N/A" }}</span>
        </div>
        <div class="stat-tile">
          <span class="stat-label">Date added</span>
          <span class="stat-value">{{ formatStatsDate(game.dateAdded) }}</span>
        </div>
        <div class="stat-tile">
          <span class="stat-label">Last played</span>
          <span class="stat-value">{{
            formatStatsDate(game.lastPlayedAt)
          }}</span>
        </div>
        <div class="stat-tile">
          <span class="stat-label">First achievement</span>
          <span class="stat-value">{{ formatStatsDate(firstUnlockedAt) }}</span>
        </div>
        <div class="stat-tile">
          <span class="stat-label">Latest achievement</span>
          <span class="stat-value">{{ formatStatsDate(lastUnlockedAt) }}</span>
        </div>
        <div class="stat-tile">
          <span class="stat-label">Purchase date</span>
          <span class="stat-value">{{
            formatStatsDate(game.ownership.purchaseDate)
          }}</span>
        </div>
        <div v-if="game.completionDate" class="stat-tile">
          <span class="stat-label">100% completed</span>
          <span class="stat-value">{{
            formatStatsDate(game.completionDate)
          }}</span>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'History'" class="history-panel">
      <h2>Metadata History</h2>
      <p v-if="fieldChangesLoading" class="empty-state">Loading…</p>
      <p v-else-if="fieldChangesError" class="empty-state">
        {{ fieldChangesError }}
      </p>
      <p v-else-if="!fieldChanges.length" class="empty-state">
        No metadata changes yet. Edits from the game form or a metadata refresh
        show up here.
      </p>
      <ul v-else class="history-list">
        <li
          v-for="change in fieldChanges"
          :key="change.id"
          class="history-entry"
        >
          <div class="history-entry-head">
            <span class="history-field">{{
              FIELD_CHANGE_LABELS[change.fieldName] || change.fieldName
            }}</span>
            <span class="history-date">{{
              formatFieldChangeDate(change.changedAt)
            }}</span>
          </div>
          <div class="history-values">
            <span class="history-old">{{ change.oldValue || "Empty" }}</span>
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
              <path d="M5 12h14" />
              <path d="M13 6l6 6-6 6" />
            </svg>
            <span class="history-new">{{ change.newValue || "Empty" }}</span>
          </div>
        </li>
      </ul>
    </section>
  </main>

  <main v-else class="not-found">
    <p>Game not found.</p>
  </main>
</template>
<style src="../styles/pages/game-detail-layout.css" />
<style src="../styles/pages/game-detail-media.css" />
