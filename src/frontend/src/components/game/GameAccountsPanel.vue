<script setup lang="ts">
import UploadDropzone from "../UploadDropzone.vue";
import MediaTile from "../MediaTile.vue";
import { useGameDetailContext } from "../../composables/gameDetailContext";
const {
  game,
  profiles,
  activeProfileId,
  newProfileName,
  profileError,
  addProfile,
  promptRenameProfile,
  removeProfile,
  selectedProfile,
  profileNoteDraft,
  profileNoteSaving,
  saveProfileNote,
  statRows,
  editingStats,
  startEditStats,
  cancelEditStats,
  addStatRow,
  removeStatRow,
  saveProfileStats,
  womUsername,
  womSyncing,
  womError,
  syncWiseOldMan,
  statHistory,
  statHistoryLoading,
  showStatHistory,
  historyShowAll,
  HISTORY_PAGE_SIZE,
  toggleStatHistory,
  formatSnapshotDate,
  statGains,
  visibleHistory,
  headlineStats,
  skillStats,
  bossStats,
  skillIconUrl,
  ACCOUNT_MEDIA_KINDS,
  accountMediaKind,
  accountMediaCategory,
  accountMediaCategories,
  accountMediaFiltered,
  checklistItems,
  checklistLoading,
  checklistError,
  newChecklistText,
  editingItemId,
  editingText,
  checklistProgress,
  checklistSections,
  collapsedSections,
  toggleSectionCollapsed,
  sectionProgress,
  addChecklistItem,
  addChecklistSection,
  toggleChecklistItem,
  startEditItem,
  commitEditItem,
  cancelEditItem,
  moveChecklistItem,
  removeChecklistItem,
  onDropError,
  onPreviewMedia,
  mediaLoading,
  mediaError,
  uploadingMedia,
  onMediaFilesSelected,
  removeMedia,
  saveMediaItem,
} = useGameDetailContext();
</script>
<template>
  <section v-if="game" class="accounts-panel">
    <div class="accounts-layout">
      <aside class="accounts-sidebar">
        <button
          type="button"
          class="account-list-item"
          :class="{ active: activeProfileId === null }"
          @click="activeProfileId = null"
        >
          <span class="account-list-name">General</span>
        </button>
        <button
          v-for="profile in profiles"
          :key="profile.id"
          type="button"
          class="account-list-item"
          :class="{ active: activeProfileId === profile.id }"
          @click="activeProfileId = profile.id"
        >
          <span class="account-list-name">{{ profile.name }}</span>
          <span v-if="profile.stats.Overall" class="account-list-meta"
            >Lvl {{ profile.stats.Overall }}</span
          >
        </button>
        <form class="account-add" @submit.prevent="void addProfile()">
          <input
            v-model="newProfileName"
            type="text"
            placeholder="Add account…"
          />
          <button
            type="submit"
            title="Add account"
            :disabled="!newProfileName.trim()"
          >
            +
          </button>
        </form>
        <div v-if="profileError" class="note-error">{{ profileError }}</div>
      </aside>

      <div class="accounts-detail">
        <div class="accounts-detail-header">
          <h2>{{ selectedProfile ? selectedProfile.name : "General" }}</h2>
          <div v-if="selectedProfile" class="accounts-detail-actions">
            <button
              type="button"
              class="small-button"
              @click="promptRenameProfile(selectedProfile)"
            >
              Rename
            </button>
            <button
              type="button"
              class="danger-button"
              @click="void removeProfile(selectedProfile)"
            >
              Delete
            </button>
          </div>
        </div>

        <template v-if="selectedProfile">
          <div class="account-note-card">
            <h3>Note</h3>
            <textarea
              v-model="profileNoteDraft"
              rows="3"
              placeholder="What are you working toward on this account?"
            ></textarea>
            <button
              type="button"
              class="small-button"
              :disabled="profileNoteSaving"
              @click="void saveProfileNote()"
            >
              {{ profileNoteSaving ? "Saving…" : "Save note" }}
            </button>
          </div>
        </template>

        <div class="checklist-card">
          <div class="checklist-card-header">
            <h3>Checklist</h3>
            <span
              v-if="checklistProgress.total"
              class="checklist-progress-label"
            >
              {{ checklistProgress.done }}/{{ checklistProgress.total }}
            </span>
          </div>
          <div v-if="checklistProgress.total" class="checklist-progress-bar">
            <div
              class="checklist-progress-fill"
              :style="{
                width: `${Math.round((checklistProgress.done / checklistProgress.total) * 100)}%`,
              }"
            ></div>
          </div>
          <div v-if="checklistError" class="note-error">
            {{ checklistError }}
          </div>
          <p v-if="checklistLoading" class="empty-state">Loading…</p>
          <p v-else-if="!checklistItems.length" class="empty-state">
            Nothing on the checklist yet.
          </p>
          <template v-else>
            <div
              v-for="section in checklistSections"
              :key="section.header?.id ?? 'default'"
              class="checklist-section"
            >
              <div
                v-if="section.header"
                class="checklist-section-header"
                @click="toggleSectionCollapsed(section.header.id)"
              >
                <span class="checklist-section-caret">{{
                  collapsedSections.has(section.header.id) ? "▸" : "▾"
                }}</span>
                <template v-if="editingItemId === section.header.id">
                  <input
                    v-model="editingText"
                    type="text"
                    class="checklist-edit-input"
                    autofocus
                    @click.stop
                    @keydown.enter="commitEditItem(section.header)"
                    @keydown.escape="cancelEditItem"
                    @blur="commitEditItem(section.header)"
                  />
                </template>
                <span
                  v-else
                  class="checklist-section-title"
                  @click.stop="startEditItem(section.header)"
                >
                  {{ section.header.text }}
                </span>
                <span class="checklist-section-count"
                  >{{ sectionProgress(section).done }}/{{
                    sectionProgress(section).total
                  }}</span
                >
                <button
                  type="button"
                  class="checklist-remove"
                  title="Delete section"
                  @click.stop="void removeChecklistItem(section.header)"
                >
                  ×
                </button>
              </div>
              <ul
                v-if="
                  !section.header || !collapsedSections.has(section.header.id)
                "
                class="checklist-items"
              >
                <li
                  v-for="item in section.items"
                  :key="item.id"
                  class="checklist-row"
                >
                  <div class="checklist-move-buttons">
                    <button
                      type="button"
                      class="checklist-move"
                      title="Move up"
                      @click="void moveChecklistItem(item, -1)"
                    >
                      ▲
                    </button>
                    <button
                      type="button"
                      class="checklist-move"
                      title="Move down"
                      @click="void moveChecklistItem(item, 1)"
                    >
                      ▼
                    </button>
                  </div>
                  <label class="checklist-label">
                    <input
                      type="checkbox"
                      :checked="item.done"
                      @change="void toggleChecklistItem(item)"
                    />
                    <input
                      v-if="editingItemId === item.id"
                      v-model="editingText"
                      type="text"
                      class="checklist-edit-input"
                      autofocus
                      @keydown.enter="commitEditItem(item)"
                      @keydown.escape="cancelEditItem"
                      @blur="commitEditItem(item)"
                    />
                    <span
                      v-else
                      :class="{ done: item.done }"
                      @click="startEditItem(item)"
                      >{{ item.text }}</span
                    >
                  </label>
                  <button
                    type="button"
                    class="checklist-remove"
                    title="Delete"
                    @click="void removeChecklistItem(item)"
                  >
                    ×
                  </button>
                </li>
              </ul>
            </div>
          </template>
          <div class="checklist-add-row">
            <form
              class="checklist-add"
              @submit.prevent="void addChecklistItem()"
            >
              <input
                v-model="newChecklistText"
                type="text"
                placeholder="Add a checklist item…"
              />
              <button
                type="submit"
                class="small-button"
                :disabled="!newChecklistText.trim()"
              >
                Add
              </button>
            </form>
            <button
              type="button"
              class="small-button"
              @click="addChecklistSection"
            >
              + Section
            </button>
          </div>
        </div>

        <div class="account-gallery-card">
          <div class="account-gallery-header">
            <h3>Media</h3>
            <div class="account-gallery-kinds">
              <button
                v-for="kind in ACCOUNT_MEDIA_KINDS"
                :key="kind"
                type="button"
                class="account-chip"
                :class="{ active: accountMediaKind === kind }"
                @click="accountMediaKind = kind"
              >
                {{ kind }}
              </button>
            </div>
          </div>

          <UploadDropzone
            :accept="
              accountMediaKind === 'screenshot'
                ? 'image/*'
                : accountMediaKind === 'clip'
                  ? 'video/*'
                  : 'audio/*'
            "
            :uploading="uploadingMedia"
            :title="`Drop ${accountMediaKind}s here`"
            :hint="`Drag and drop, or click to browse, tagged to ${selectedProfile ? selectedProfile.name : 'General'}`"
            @files-selected="onMediaFilesSelected"
            @drop-error="onDropError"
          />
          <div v-if="mediaError" class="form-error">{{ mediaError }}</div>

          <div v-if="accountMediaCategories.length" class="account-bar">
            <button
              type="button"
              class="account-chip"
              :class="{ active: accountMediaCategory === null }"
              @click="accountMediaCategory = null"
            >
              All
            </button>
            <button
              v-for="category in accountMediaCategories"
              :key="category"
              type="button"
              class="account-chip"
              :class="{ active: accountMediaCategory === category }"
              @click="accountMediaCategory = category"
            >
              {{ category }}
            </button>
          </div>

          <p v-if="mediaLoading" class="empty-row">Loading…</p>
          <p v-else-if="!accountMediaFiltered.length" class="empty-row">
            No {{ accountMediaKind }}s yet.
          </p>
          <div v-else class="media-grid">
            <MediaTile
              v-for="item in accountMediaFiltered"
              :key="item.id"
              :item="item"
              :achievements="game.achievements"
              :profiles="profiles"
              @preview="onPreviewMedia($event.url)"
              @delete="removeMedia"
              @save="saveMediaItem"
            />
          </div>
        </div>

        <div v-if="selectedProfile" class="account-stats-card">
          <div class="account-stats-header">
            <h3>Stats</h3>
            <button
              v-if="!editingStats"
              type="button"
              class="small-button"
              @click="startEditStats"
            >
              Edit
            </button>
          </div>
          <div v-if="game.osrsStatsEnabled" class="wom-sync-row">
            <input
              v-model="womUsername"
              type="text"
              placeholder="RuneScape username (WiseOldMan)"
            />
            <button
              type="button"
              class="small-button"
              :disabled="womSyncing"
              @click="void syncWiseOldMan()"
            >
              {{ womSyncing ? "Syncing…" : "Sync from WiseOldMan" }}
            </button>
          </div>
          <div v-if="womError" class="note-error">{{ womError }}</div>

          <p
            v-if="!editingStats && !Object.keys(selectedProfile.stats).length"
            class="empty-state small"
          >
            No stats yet, add one manually{{
              game.osrsStatsEnabled ? ", or sync from WiseOldMan above" : ""
            }}.
          </p>
          <template v-else-if="!editingStats && game.osrsStatsEnabled">
            <div v-if="headlineStats.length" class="stat-grid headline">
              <div
                v-for="entry in headlineStats"
                :key="entry.key"
                class="account-stat-tile headline"
              >
                <img
                  :src="skillIconUrl(entry.key)"
                  alt=""
                  class="stat-tile-icon"
                  @error="
                    ($event.target as HTMLElement).style.visibility = 'hidden'
                  "
                />
                <span class="stat-tile-label">{{ entry.key }}</span>
                <span class="stat-tile-value">{{ entry.value }}</span>
              </div>
            </div>
            <template v-if="skillStats.length">
              <h4 class="stat-group-heading">Skills</h4>
              <div class="stat-grid">
                <div
                  v-for="[key, value] in skillStats"
                  :key="key"
                  class="account-stat-tile"
                >
                  <img
                    :src="skillIconUrl(key)"
                    alt=""
                    class="stat-tile-icon"
                    @error="
                      ($event.target as HTMLElement).style.visibility = 'hidden'
                    "
                  />
                  <span class="stat-tile-label">{{ key }}</span>
                  <span class="stat-tile-value">{{ value }}</span>
                </div>
              </div>
            </template>
            <template v-if="bossStats.length">
              <h4 class="stat-group-heading">Bosses &amp; Activities</h4>
              <div class="stat-grid">
                <div
                  v-for="[key, value] in bossStats"
                  :key="key"
                  class="account-stat-tile"
                >
                  <svg
                    viewBox="0 0 24 24"
                    width="20"
                    height="20"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.6"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="stat-tile-boss-icon"
                  >
                    <path d="M6.5 2 3 6l3.5 2M17.5 2 21 6l-3.5 2" />
                    <path
                      d="M12 2c-3 0-5 2-5 5 0 2.5 1.5 4 2 5.5L8 21h8l-1-8.5c.5-1.5 2-3 2-5.5 0-3-2-5-5-5z"
                    />
                    <circle
                      cx="9.5"
                      cy="8"
                      r="1"
                      fill="currentColor"
                      stroke="none"
                    />
                    <circle
                      cx="14.5"
                      cy="8"
                      r="1"
                      fill="currentColor"
                      stroke="none"
                    />
                  </svg>
                  <span class="stat-tile-label">{{ key }}</span>
                  <span class="stat-tile-value">{{ value }}</span>
                </div>
              </div>
            </template>
          </template>
          <div v-else-if="!editingStats" class="stat-grid">
            <div
              v-for="(value, key) in selectedProfile.stats"
              :key="key"
              class="account-stat-tile"
            >
              <span class="stat-tile-label">{{ key }}</span>
              <span class="stat-tile-value">{{ value }}</span>
            </div>
          </div>

          <template v-else>
            <div v-if="statRows.length" class="stat-rows">
              <div
                v-for="(row, index) in statRows"
                :key="index"
                class="stat-row"
              >
                <input
                  v-model="row.key"
                  type="text"
                  placeholder="Label (e.g. Overall)"
                />
                <input v-model="row.value" type="text" placeholder="Value" />
                <button
                  type="button"
                  class="checklist-remove"
                  title="Remove"
                  @click="removeStatRow(index)"
                >
                  ×
                </button>
              </div>
            </div>
            <div class="stat-actions">
              <button type="button" class="small-button" @click="addStatRow">
                + Add stat
              </button>
              <button
                type="button"
                class="small-button"
                @click="cancelEditStats"
              >
                Cancel
              </button>
              <button
                type="button"
                class="primary-button"
                @click="void saveProfileStats()"
              >
                Save stats
              </button>
            </div>
          </template>
        </div>

        <div v-if="selectedProfile" class="account-history-card">
          <button
            type="button"
            class="account-history-toggle"
            @click="void toggleStatHistory()"
          >
            <span>History</span>
            <span class="account-history-caret">{{
              showStatHistory ? "▾" : "▸"
            }}</span>
          </button>
          <div v-if="showStatHistory">
            <p v-if="statHistoryLoading" class="empty-state small">Loading…</p>
            <p v-else-if="!statHistory.length" class="empty-state small">
              No history yet, it builds up automatically every time you sync or
              save stats.
            </p>
            <template v-else>
              <ul class="stat-history-list">
                <li
                  v-for="snapshot in visibleHistory"
                  :key="snapshot.id"
                  class="stat-history-row"
                >
                  <span class="stat-history-date">{{
                    formatSnapshotDate(snapshot.recorded_at)
                  }}</span>
                  <span
                    v-if="statGains[snapshot.id]?.length"
                    class="stat-history-values"
                  >
                    <span
                      v-for="line in statGains[snapshot.id]"
                      :key="line"
                      class="stat-history-chip gain"
                      >{{ line }}</span
                    >
                  </span>
                  <span v-else class="stat-history-values">
                    <span
                      v-for="(value, key) in snapshot.stats"
                      :key="key"
                      class="stat-history-chip"
                      >{{ key }}: {{ value }}</span
                    >
                  </span>
                </li>
              </ul>
              <button
                v-if="!historyShowAll && statHistory.length > HISTORY_PAGE_SIZE"
                type="button"
                class="small-button"
                @click="historyShowAll = true"
              >
                Show all {{ statHistory.length }}
              </button>
            </template>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
