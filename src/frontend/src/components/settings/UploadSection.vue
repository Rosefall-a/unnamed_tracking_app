<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
defineProps<{ standalone?: boolean }>();
import { fetchUploadLimits } from "../../services/settings";
import { fetchGames } from "../../services/games";
import type { Game } from "../../types/game";
import UploadDropzone from "../UploadDropzone.vue";
import UiModal from "../UiModal.vue";
import {
  uploadToInbox,
  listInbox,
  deleteInboxMedia,
  assignInboxMedia,
  fetchInboxTrash,
  restoreInboxMedia,
} from "../../services/media";
import type { InboxMediaItem, TrashedInboxItem } from "../../services/media";
import {
  startTask,
  updateTask,
  completeTask,
  errorTask,
  addFeedItem,
  setTaskRetry,
} from "../../state/taskProgress";
import { refreshInboxCount } from "../../state/inbox";

const maxUploadSizeMb = ref<number | null>(null);

onMounted(async () => {
  try {
    const limits = await fetchUploadLimits();
    maxUploadSizeMb.value = limits.max_upload_size_mb;
  } catch {
    // non-critical, the upload flow below still works without this number
  }
});

const games = ref<Game[]>([]);
onMounted(async () => {
  try {
    games.value = await fetchGames();
  } catch {
    // game picker just stays empty; assign still shows an error if attempted
  }
});

const inboxMedia = ref<InboxMediaItem[]>([]);
const loadingInbox = ref(true);
const inboxError = ref<string | null>(null);

function pruneSelectionToCurrentItems() {
  const currentKeys = new Set(inboxMedia.value.map(itemKey));
  const pruned = new Set(
    [...selected.value].filter((key) => currentKeys.has(key)),
  );
  if (pruned.size !== selected.value.size) selected.value = pruned;
}

async function loadInbox() {
  loadingInbox.value = true;
  inboxError.value = null;
  try {
    inboxMedia.value = await listInbox();
    // a partially-failed bulk action can leave `selected` pointing at items
    // that got assigned/deleted and are gone from this fresh list, drop
    // those rather than let the selection count lie
    pruneSelectionToCurrentItems();
  } catch (err) {
    inboxError.value =
      err instanceof Error ? err.message : "Failed to load uploads";
  } finally {
    loadingInbox.value = false;
  }
  void refreshInboxCount();
}
onMounted(loadInbox);

const screenshots = computed(() =>
  inboxMedia.value.filter((m) => m.kind === "screenshot"),
);
const clips = computed(() => inboxMedia.value.filter((m) => m.kind === "clip"));

const uploading = ref(false);
const uploadSummary = ref<string | null>(null);
const uploadError = ref<string | null>(null);

async function onFilesSelected(files: File[]) {
  if (!files.length) return;

  uploading.value = true;
  uploadSummary.value = null;
  uploadError.value = null;
  // real byte-level progress against the actual upload (not a fake jump to
  // 100%), see uploadToInbox/uploadFiles in services/media.ts
  const taskId = startTask(
    `Uploading ${files.length} file${files.length === 1 ? "" : "s"}`,
    100,
  );

  const attempt = async () => {
    try {
      const results = await uploadToInbox(files, (fraction, speedLabel) =>
        updateTask(taskId, Math.round(fraction * 100), undefined, speedLabel),
      );
      const saved = results.filter((r) => r.status === "saved");
      const rejected = results.filter((r) => r.status === "rejected");
      uploadSummary.value = `${saved.length} uploaded${rejected.length ? `, ${rejected.length} rejected` : ""}.`;
      for (const r of results) {
        addFeedItem(
          taskId,
          r.status === "saved"
            ? `${r.filename} uploaded`
            : `${r.filename}: ${r.reason ?? "rejected"}`,
        );
      }
      if (saved.length === 0 && rejected.length > 0) {
        errorTask(taskId, uploadSummary.value);
      } else {
        completeTask(taskId, uploadSummary.value);
      }
      await loadInbox();
    } catch (err) {
      uploadError.value = err instanceof Error ? err.message : "Upload failed";
      errorTask(taskId, uploadError.value);
      setTaskRetry(taskId, () => void attempt());
    } finally {
      uploading.value = false;
    }
  };
  await attempt();
}
function onDropError(message: string) {
  uploadError.value = message;
}

const selected = ref<Set<string>>(new Set());
function itemKey(item: { kind: string; filename: string }) {
  return `${item.kind}:${item.filename}`;
}
function toggleSelected(item: InboxMediaItem) {
  const key = itemKey(item);
  if (selected.value.has(key)) selected.value.delete(key);
  else selected.value.add(key);
  selected.value = new Set(selected.value);
}
const selectedCount = computed(() => selected.value.size);
const allSelected = computed(
  () =>
    inboxMedia.value.length > 0 &&
    selectedCount.value === inboxMedia.value.length,
);
function toggleSelectAll() {
  selected.value = allSelected.value
    ? new Set()
    : new Set(inboxMedia.value.map(itemKey));
}

// ---- game picker: type to filter, pick from a list with cover art ----
const assignTargetGameId = ref("");
const gameQuery = ref("");
const gamePickerOpen = ref(false);
const gamePickerRoot = ref<HTMLElement | null>(null);
const gamePickerSearchInput = ref<HTMLInputElement | null>(null);
const assigning = ref(false);
const assignError = ref<string | null>(null);

const selectedGame = computed(
  () => games.value.find((g) => g.id === assignTargetGameId.value) ?? null,
);
const filteredGames = computed(() => {
  const q = gameQuery.value.trim().toLowerCase();
  const list = q
    ? games.value.filter((g) => g.title.toLowerCase().includes(q))
    : games.value;
  return list.slice(0, 40);
});
async function openGamePicker() {
  gamePickerOpen.value = true;
  gameQuery.value = "";
  // The `autofocus` attribute doesn't reliably fire on an element inserted
  // after page load (this input only exists once `gamePickerOpen` flips),
  // so it's focused explicitly here instead.
  await nextTick();
  gamePickerSearchInput.value?.focus();
}
function pickGame(game: Game) {
  assignTargetGameId.value = game.id;
  gamePickerOpen.value = false;
  gameQuery.value = "";
}
// A real click-outside check, not a blur timeout: focus moving from the
// trigger button to the search input it just opened used to fire the
// trigger's own blur handler and close the menu before a letter could be
// typed. This only closes when the click actually lands outside the
// picker.
function onDocumentClick(e: MouseEvent) {
  if (!gamePickerOpen.value) return;
  if (!gamePickerRoot.value?.contains(e.target as Node)) {
    gamePickerOpen.value = false;
  }
}
onMounted(() => document.addEventListener("mousedown", onDocumentClick));
onBeforeUnmount(() =>
  document.removeEventListener("mousedown", onDocumentClick),
);

async function assignSelected() {
  if (!assignTargetGameId.value || !selected.value.size) return;
  assigning.value = true;
  assignError.value = null;
  try {
    const items = inboxMedia.value.filter((m) =>
      selected.value.has(itemKey(m)),
    );
    for (const item of items) {
      await assignInboxMedia(
        item.kind,
        item.filename,
        assignTargetGameId.value,
      );
    }
    selected.value = new Set();
    assignTargetGameId.value = "";
  } catch (err) {
    assignError.value =
      err instanceof Error ? err.message : "Failed to assign media";
  } finally {
    // always reload, not just on the success path, a failure partway
    // through the loop still assigned some items, so the list needs to
    // reflect that rather than keep showing them as still unassigned
    await loadInbox();
    assigning.value = false;
  }
}

const deleting = ref(false);
const deleteError = ref<string | null>(null);
const confirmingBulkDelete = ref(false);

async function removeItem(item: InboxMediaItem) {
  deleteError.value = null;
  try {
    await deleteInboxMedia(item.kind, item.filename);
    selected.value.delete(itemKey(item));
    await loadInbox();
    await refreshTrash();
  } catch (err) {
    deleteError.value =
      err instanceof Error ? err.message : "Failed to delete media";
  }
}

async function deleteSelected() {
  confirmingBulkDelete.value = false;
  if (!selected.value.size) return;
  deleting.value = true;
  deleteError.value = null;
  try {
    const items = inboxMedia.value.filter((m) =>
      selected.value.has(itemKey(m)),
    );
    for (const item of items) {
      await deleteInboxMedia(item.kind, item.filename);
    }
  } catch (err) {
    deleteError.value =
      err instanceof Error ? err.message : "Failed to delete media";
  } finally {
    // always reload, not just on the success path, see assignSelected
    await loadInbox();
    await refreshTrash();
    deleting.value = false;
  }
}

function formatItemDate(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

// --- Trash: soft-deleted uploads stay recoverable for 7 days before
// the background sweep purges them for good (features/trash/sweep.py) ----
const inboxTrash = ref<TrashedInboxItem[]>([]);
const showTrash = ref(false);

async function refreshTrash() {
  try {
    inboxTrash.value = await fetchInboxTrash();
  } catch {
    // trash listing failing silently isn't worth blocking the main view
  }
}
onMounted(refreshTrash);

function daysUntil(unixSeconds: number): number {
  return Math.max(0, Math.ceil((unixSeconds - Date.now() / 1000) / 86400));
}

async function restoreItem(item: TrashedInboxItem) {
  try {
    await restoreInboxMedia(item.kind, item.filename);
    await loadInbox();
    await refreshTrash();
  } catch (err) {
    deleteError.value =
      err instanceof Error ? err.message : "Failed to restore media";
  }
}
</script>

<template>
  <section class="settings-section">
    <h2 v-if="!standalone">Upload</h2>
    <p class="section-hint">
      Bulk-upload screenshots and clips without picking a game first: drop in
      everything at once, then group and assign them below. Images become
      screenshots, videos become clips automatically.
      <template v-if="maxUploadSizeMb"
        >Each file must be under {{ maxUploadSizeMb }} MB.</template
      >
    </p>

    <UploadDropzone
      accept="image/*,video/*"
      :uploading="uploading"
      title="Drop screenshots or clips here"
      hint="Drag and drop, or click to browse — any number at once"
      @files-selected="onFilesSelected"
      @drop-error="onDropError"
    />

    <div v-if="uploadSummary" class="form-success">{{ uploadSummary }}</div>
    <div v-if="uploadError" class="form-error">{{ uploadError }}</div>

    <div class="settings-divider"></div>

    <div class="inbox-header">
      <h3>
        Unassigned
        <span v-if="inboxMedia.length" class="count-pill">{{
          inboxMedia.length
        }}</span>
      </h3>
      <button
        type="button"
        class="icon-text-button"
        :disabled="!inboxMedia.length"
        @click="toggleSelectAll"
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
          <path d="M20 6L9 17l-5-5" />
        </svg>
        {{ allSelected ? "Deselect all" : "Select all" }}
      </button>
    </div>

    <div v-if="selectedCount" class="assign-bar">
      <span class="assign-count">{{ selectedCount }} selected</span>

      <div ref="gamePickerRoot" class="game-picker">
        <button
          type="button"
          class="game-picker-trigger"
          @click="openGamePicker"
        >
          <span
            v-if="selectedGame?.coverImageUrl"
            class="game-picker-cover"
            :style="{ backgroundImage: `url(${selectedGame.coverImageUrl})` }"
          ></span>
          <svg
            v-else
            class="game-picker-icon"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <rect x="2" y="7" width="20" height="10" rx="4" />
            <line x1="7" y1="12" x2="9" y2="12" />
            <line x1="8" y1="11" x2="8" y2="13" />
            <circle cx="16" cy="11" r="0.8" fill="currentColor" />
            <circle cx="18" cy="13" r="0.8" fill="currentColor" />
          </svg>
          <span class="game-picker-label">{{
            selectedGame ? selectedGame.title : "Assign to a game…"
          }}</span>
          <svg
            class="game-picker-caret"
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
        <div v-if="gamePickerOpen" class="game-picker-menu">
          <input
            ref="gamePickerSearchInput"
            v-model="gameQuery"
            type="text"
            class="game-picker-search"
            placeholder="Search your games…"
            @mousedown.stop
          />
          <div class="game-picker-list">
            <button
              v-for="game in filteredGames"
              :key="game.id"
              type="button"
              class="game-picker-option"
              :class="{ active: game.id === assignTargetGameId }"
              @mousedown.prevent="pickGame(game)"
            >
              <span
                v-if="game.coverImageUrl"
                class="game-picker-option-cover"
                :style="{ backgroundImage: `url(${game.coverImageUrl})` }"
              ></span>
              <span v-else class="game-picker-option-cover placeholder"></span>
              <span class="game-picker-option-text">
                <span class="game-picker-option-title">{{ game.title }}</span>
                <span
                  v-if="game.platforms.length"
                  class="game-picker-option-platform"
                  >{{ game.platforms.map((p) => p.platform).join(", ") }}</span
                >
              </span>
            </button>
            <p v-if="!filteredGames.length" class="game-picker-empty">
              No games match "{{ gameQuery }}"
            </p>
          </div>
        </div>
      </div>

      <button
        type="button"
        class="primary-button"
        :disabled="!assignTargetGameId || assigning"
        @click="assignSelected"
      >
        {{ assigning ? "Assigning…" : "Assign" }}
      </button>
      <button
        type="button"
        class="danger-icon-button"
        title="Delete selected"
        aria-label="Delete selected"
        :disabled="deleting"
        @click="confirmingBulkDelete = true"
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
          <path d="M3 6h18" />
          <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
        </svg>
        {{ deleting ? "Deleting…" : `Delete (${selectedCount})` }}
      </button>
    </div>
    <div v-if="assignError" class="form-error">{{ assignError }}</div>
    <div v-if="deleteError" class="form-error">{{ deleteError }}</div>

    <p v-if="loadingInbox">Loading…</p>
    <p v-else-if="inboxError" class="form-error">{{ inboxError }}</p>
    <template v-else>
      <p v-if="!inboxMedia.length" class="empty-hint">
        Nothing waiting to be sorted: dropped files with no game picked land
        here.
      </p>

      <div v-if="screenshots.length" class="media-group">
        <span class="media-group-label">Screenshots</span>
        <div class="media-grid">
          <div
            v-for="item in screenshots"
            :key="itemKey(item)"
            class="media-item"
          >
            <div
              class="media-thumb"
              :class="{ selected: selected.has(itemKey(item)) }"
            >
              <button
                type="button"
                class="media-select"
                :aria-label="`Select screenshot: ${item.filename}`"
                :aria-pressed="selected.has(itemKey(item))"
                @click="toggleSelected(item)"
              >
                <div
                  class="select-check"
                  :class="{ checked: selected.has(itemKey(item)) }"
                >
                  <svg
                    v-if="selected.has(itemKey(item))"
                    viewBox="0 0 24 24"
                    width="14"
                    height="14"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="3"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                </div>
                <img :src="item.url" alt="" />
              </button>
              <button
                type="button"
                class="remove-button"
                title="Delete"
                @click.stop="removeItem(item)"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.4"
                  stroke-linecap="round"
                >
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <span class="media-date">{{
              formatItemDate(item.created_at)
            }}</span>
          </div>
        </div>
      </div>

      <div v-if="clips.length" class="media-group">
        <span class="media-group-label">Clips</span>
        <div class="media-grid">
          <div v-for="item in clips" :key="itemKey(item)" class="media-item">
            <div
              class="media-thumb clip"
              :class="{ selected: selected.has(itemKey(item)) }"
            >
              <button
                type="button"
                class="media-select"
                :aria-label="`Select clip: ${item.filename}`"
                :aria-pressed="selected.has(itemKey(item))"
                @click="toggleSelected(item)"
              >
                <div
                  class="select-check"
                  :class="{ checked: selected.has(itemKey(item)) }"
                >
                  <svg
                    v-if="selected.has(itemKey(item))"
                    viewBox="0 0 24 24"
                    width="14"
                    height="14"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="3"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                </div>
                <video :src="item.url" muted></video>
                <span class="clip-badge">
                  <svg
                    viewBox="0 0 24 24"
                    width="13"
                    height="13"
                    fill="currentColor"
                  >
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </span>
              </button>
              <button
                type="button"
                class="remove-button"
                title="Delete"
                @click.stop="removeItem(item)"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.4"
                  stroke-linecap="round"
                >
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <span class="media-date">{{
              formatItemDate(item.created_at)
            }}</span>
          </div>
        </div>
      </div>

      <div v-if="inboxTrash.length" class="trash-section">
        <button
          type="button"
          class="trash-toggle"
          @click="showTrash = !showTrash"
        >
          <svg
            class="trash-toggle-caret"
            :class="{ open: showTrash }"
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M9 18l6-6-6-6" />
          </svg>
          Recently deleted ({{ inboxTrash.length }})
        </button>
        <ul v-if="showTrash" class="trash-list">
          <li v-for="item in inboxTrash" :key="itemKey(item)" class="trash-row">
            <span class="trash-name">{{
              item.filename.split("_").slice(1).join("_")
            }}</span>
            <span class="trash-meta"
              >purges in {{ daysUntil(item.purge_at) }}d</span
            >
            <button
              type="button"
              class="icon-text-button small"
              @click="restoreItem(item)"
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
                <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
                <path d="M3 3v5h5" />
              </svg>
              Restore
            </button>
          </li>
        </ul>
      </div>
    </template>

    <UiModal
      v-if="confirmingBulkDelete"
      :title="`Delete ${selectedCount} item${selectedCount === 1 ? '' : 's'}?`"
      description="Moved to trash: recoverable for 7 days, then purged for good."
      @close="confirmingBulkDelete = false"
    >
      <template #footer>
        <button
          type="button"
          class="secondary-button"
          @click="confirmingBulkDelete = false"
        >
          Cancel
        </button>
        <button type="button" class="danger-button" @click="deleteSelected">
          Delete
        </button>
      </template>
    </UiModal>
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 12px;
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
  color: var(--ui-text);
}
.settings-section h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: var(--ui-text);
}
.count-pill {
  background: color-mix(in srgb, var(--ui-text) 8%, transparent);
  color: var(--ui-dim);
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}
.section-hint {
  color: var(--ui-dim);
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 16px;
}
.settings-divider {
  height: 1px;
  background: var(--ui-border);
  margin: 20px 0;
}
.form-error {
  color: var(--ui-error);
  font-size: 13px;
  background: var(--ui-danger-soft);
  border: 1px solid color-mix(in srgb, var(--ui-error) 40%, var(--ui-border));
  border-radius: var(--ui-radius-control);
  padding: 8px 10px;
  margin-top: 10px;
}
.form-success {
  color: var(--ui-good);
  font-size: 13px;
  background: color-mix(in srgb, var(--ui-good) 10%, var(--ui-surface));
  border: 1px solid color-mix(in srgb, var(--ui-good) 40%, var(--ui-border));
  border-radius: var(--ui-radius-control);
  padding: 8px 10px;
  margin-top: 10px;
}
.inbox-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.assign-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  background: color-mix(in srgb, var(--ui-accent) 6%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-accent) 25%, transparent);
  border-radius: var(--ui-radius-control);
  padding: 10px 12px;
  margin-bottom: 14px;
}
.assign-count {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--ui-accent-text);
  white-space: nowrap;
}

/* ---- game picker ---- */
.game-picker {
  position: relative;
  flex: 1;
  min-width: 220px;
}
.game-picker-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  box-sizing: border-box;
  background: var(--ui-bg);
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 8px 12px;
  font: inherit;
  font-size: 0.84rem;
  cursor: pointer;
  text-align: left;
}
.game-picker-trigger:hover {
  border-color: var(--ui-border-strong);
}
.game-picker-cover {
  width: 26px;
  height: 34px;
  border-radius: 4px;
  background-size: cover;
  background-position: center;
  flex-shrink: 0;
}
.game-picker-icon {
  color: var(--ui-faint);
  flex-shrink: 0;
}
.game-picker-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.game-picker-caret {
  color: var(--ui-faint);
  flex-shrink: 0;
}
.game-picker-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  min-width: 280px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  box-shadow: var(--ui-elevation);
  z-index: 30;
  padding: 8px;
}
.game-picker-search {
  width: 100%;
  box-sizing: border-box;
  background: var(--ui-bg);
  border: 1px solid var(--ui-border);
  border-radius: 7px;
  color: var(--ui-text);
  padding: 8px 10px;
  font: inherit;
  font-size: 0.82rem;
  margin-bottom: 6px;
}
.game-picker-search:focus {
  outline: none;
  border-color: var(--ui-accent);
}
.game-picker-list {
  max-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.game-picker-option {
  display: flex;
  align-items: center;
  gap: 10px;
  background: none;
  border: none;
  border-radius: 7px;
  padding: 6px 8px;
  cursor: pointer;
  text-align: left;
}
.game-picker-option:hover {
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
}
.game-picker-option.active {
  background: color-mix(in srgb, var(--ui-accent) 16%, transparent);
}
.game-picker-option-cover {
  width: 30px;
  height: 40px;
  border-radius: 4px;
  background-size: cover;
  background-position: center;
  flex-shrink: 0;
}
.game-picker-option-cover.placeholder {
  background: var(--ui-surface-2);
}
.game-picker-option-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.game-picker-option-title {
  font-size: 0.84rem;
  color: var(--ui-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.game-picker-option-platform {
  font-size: 0.7rem;
  color: var(--ui-faint);
}
.game-picker-empty {
  margin: 0;
  padding: 10px 8px;
  color: var(--ui-faint);
  font-size: 0.82rem;
}

.primary-button {
  min-height: 44px;
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 8px 16px;
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
  white-space: nowrap;
}
.primary-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.secondary-button,
.danger-button {
  min-height: 44px;
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 8px 16px;
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
}
.secondary-button {
  background: color-mix(in srgb, var(--ui-text) 8%, transparent);
  color: var(--ui-text);
}
.secondary-button:hover {
  background: color-mix(in srgb, var(--ui-text) 14%, transparent);
}
.danger-button {
  background: var(--ui-danger-soft);
  color: var(--ui-error);
}
.danger-button:hover {
  background: var(--ui-danger-soft);
}
.danger-icon-button {
  min-height: 44px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--ui-danger-soft);
  border: 1px solid color-mix(in srgb, var(--ui-error) 40%, var(--ui-border));
  color: var(--ui-error);
  border-radius: var(--ui-radius-control);
  padding: 8px 14px;
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
  white-space: nowrap;
}
.danger-icon-button:hover:not(:disabled) {
  background: var(--ui-danger-soft);
}
.danger-icon-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.icon-text-button {
  display: flex;
  align-items: center;
  gap: 6px;
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  border: 1px solid var(--ui-border);
  color: var(--ui-text);
  border-radius: var(--ui-radius-control);
  padding: 7px 12px;
  font: inherit;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}
.icon-text-button:hover:not(:disabled) {
  border-color: var(--ui-border-strong);
  color: var(--ui-text);
}
.icon-text-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.icon-text-button.small {
  min-height: 44px;
  padding: 5px 10px;
  font-size: 0.76rem;
}
.empty-hint {
  color: var(--ui-faint);
  font-size: 0.9rem;
}
.media-group {
  margin-bottom: 22px;
}
.media-group-label {
  display: block;
  color: var(--ui-dim);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 10px;
}
.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 14px;
}
.media-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.media-date {
  color: var(--ui-faint);
  font-size: 0.74rem;
  text-align: center;
}
.media-thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: var(--ui-radius-control);
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  background: var(--ui-bg);
  transition:
    border-color 0.15s ease,
    transform 0.15s ease;
}
.media-thumb:hover {
  transform: translateY(-2px);
}
.media-select {
  display: block;
  width: 100%;
  height: 100%;
  padding: 0;
  border: 0;
  background: var(--ui-surface-2);
  cursor: pointer;
}
.media-select:focus-visible {
  outline: 3px solid var(--ui-accent);
  outline-offset: -4px;
}
.media-thumb img,
.media-thumb video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.media-thumb.selected {
  border-color: var(--ui-accent);
}
.select-check {
  position: absolute;
  top: 6px;
  left: 6px;
  width: 24px;
  height: 24px;
  border-radius: 7px;
  border: 2px solid color-mix(in srgb, var(--ui-text) 55%, transparent);
  background: var(--ui-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ui-text);
  z-index: 1;
}
.select-check.checked {
  background: var(--ui-accent);
  border-color: var(--ui-accent);
  color: var(--ui-on-accent);
}
.clip-badge {
  position: absolute;
  bottom: 6px;
  left: 6px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--ui-surface);
  color: var(--ui-text);
  display: flex;
  align-items: center;
  justify-content: center;
}
.remove-button {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: var(--ui-surface);
  color: var(--ui-text);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.remove-button:hover {
  background: var(--ui-danger-soft);
  color: var(--ui-error);
}
.trash-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--ui-border);
}
.trash-toggle {
  min-height: 44px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: var(--ui-dim);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0;
}
.trash-toggle:hover {
  color: var(--ui-text);
}
.trash-toggle-caret {
  transition: transform 0.15s ease;
}
.trash-toggle-caret.open {
  transform: rotate(90deg);
}
.trash-list {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.trash-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: color-mix(in srgb, var(--ui-text) 3%, transparent);
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-control);
  font-size: 0.82rem;
}
.trash-name {
  flex: 1;
  color: var(--ui-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trash-meta {
  color: var(--ui-faint);
  font-size: 0.76rem;
}
</style>
