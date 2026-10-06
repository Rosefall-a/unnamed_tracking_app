<script setup lang="ts">
// The "add to collection" button on a game page. A copy of the Lists button
// on the Media pages (MediaExtrasPanel): same round icon with a count, same
// popover with a checkbox per collection, a box to create a new one, and a
// link to the full page. Collections here are names on the game itself (plus
// empty ones kept in localStorage), so there is no rename or delete in the
// popover; those stay on the Collections page.
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import {
  fetchGames,
  addGameToCollection,
  removeGameFromCollection,
} from "../services/games";
import { smartCollections } from "../state/smartCollections";
import { blurOnLeave } from "../utils/blurOnLeave";
import type { Game } from "../types/game";

const props = defineProps<{ game: Game }>();
const emit = defineEmits<{ changed: [collections: string[]] }>();

const MANUAL_KEY = "manualCollections";
const COVER_KEY = "collectionCoverPicks";

const router = useRouter();
const root = ref<HTMLElement | null>(null);
const listBtn = ref<HTMLElement | null>(null);
const open = ref(false);
const popoverStyle = ref<{ top: string; left: string }>({
  top: "0px",
  left: "0px",
});

interface Row {
  name: string;
  count: number;
}
const rows = ref<Row[]>([]);
const loaded = ref(false);
const busy = ref<string | null>(null);
const error = ref<string | null>(null);
const newName = ref("");
const covers = ref<Record<string, string>>({});

const memberOf = computed(() => new Set(props.game.collections));

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

async function load() {
  error.value = null;
  try {
    const games = await fetchGames();
    const counts = new Map<string, number>();
    for (const g of games) {
      for (const c of g.collections) counts.set(c, (counts.get(c) ?? 0) + 1);
    }
    for (const n of readJson<string[]>(MANUAL_KEY, [])) {
      if (!counts.has(n)) counts.set(n, 0);
    }
    // smart collections fill themselves from a rule, so they are never an add target
    const smart = new Set(smartCollections.value.map((c) => c.name));
    rows.value = [...counts.entries()]
      .filter(([name]) => !smart.has(name))
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => a.name.localeCompare(b.name));
    covers.value = readJson<Record<string, string>>(COVER_KEY, {});
    loaded.value = true;
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Failed to load collections.";
  }
}

async function toggle(name: string) {
  busy.value = name;
  error.value = null;
  try {
    const was = memberOf.value.has(name);
    const updated = was
      ? await removeGameFromCollection(props.game.id, name)
      : await addGameToCollection(props.game.id, name);
    emit("changed", updated.collections);
    const row = rows.value.find((r) => r.name === name);
    if (row) row.count += was ? -1 : 1;
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Failed to update collection.";
  } finally {
    busy.value = null;
  }
}

async function submitNew() {
  const name = newName.value.trim();
  if (!name) return;
  if (rows.value.some((r) => r.name.toLowerCase() === name.toLowerCase())) {
    error.value = `"${name}" already exists.`;
    return;
  }
  try {
    const updated = await addGameToCollection(props.game.id, name);
    emit("changed", updated.collections);
    rows.value = [...rows.value, { name, count: 1 }].sort((a, b) =>
      a.name.localeCompare(b.name),
    );
    newName.value = "";
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Failed to create collection.";
  }
}

function useAsCover(name: string) {
  covers.value = { ...covers.value, [name]: props.game.id };
  try {
    localStorage.setItem(COVER_KEY, JSON.stringify(covers.value));
  } catch {
    // the cover just won't survive a reload
  }
}

function goToCollections() {
  open.value = false;
  router.push("/games/collections");
}

async function togglePopover() {
  open.value = !open.value;
  if (!open.value) return;
  const rect = listBtn.value?.getBoundingClientRect();
  if (rect) {
    popoverStyle.value = {
      top: `${rect.bottom + 10}px`,
      left: `${Math.max(16, Math.min(rect.left, window.innerWidth - 296))}px`,
    };
  }
  await load();
}

function onDocumentClick(e: MouseEvent) {
  const target = e.target as Node;
  const insideTrigger = root.value?.contains(target);
  const insidePopover = (target as HTMLElement).closest?.(".popover");
  if (!insideTrigger && !insidePopover) open.value = false;
}
onMounted(() => document.addEventListener("click", onDocumentClick));
onBeforeUnmount(() => document.removeEventListener("click", onDocumentClick));
</script>

<template>
  <div ref="root" class="media-extras">
    <div class="extras-item">
      <button
        ref="listBtn"
        type="button"
        class="icon-btn"
        :class="{ active: game.collections.length > 0 }"
        title="Add to collection"
        @click.stop="togglePopover"
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
          <path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01" />
        </svg>
        <span v-if="game.collections.length" class="badge-count">{{
          game.collections.length
        }}</span>
      </button>
    </div>
  </div>

  <Teleport to="body">
    <Transition name="pop">
      <div
        v-if="open"
        class="popover"
        :style="{ top: popoverStyle.top, left: popoverStyle.left }"
        @click.stop
      >
        <div class="popover-header">
          <svg
            class="popover-icon"
            viewBox="0 0 24 24"
            width="15"
            height="15"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01" />
          </svg>
          <p class="popover-title">Add to collection</p>
        </div>

        <p v-if="error" class="extras-error">{{ error }}</p>
        <p v-if="loaded && !rows.length" class="empty-hint">
          No collections yet. Create one below.
        </p>
        <ul v-else class="list-options">
          <li
            v-for="r in rows"
            :key="r.name"
            class="list-row"
            @mouseleave="blurOnLeave"
          >
            <button
              type="button"
              class="list-option"
              :class="{ checked: memberOf.has(r.name) }"
              :disabled="busy === r.name"
              @click="toggle(r.name)"
            >
              <span class="list-check">
                <svg
                  v-if="memberOf.has(r.name)"
                  viewBox="0 0 24 24"
                  width="12"
                  height="12"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="3"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </span>
              <span class="list-option-name">{{ r.name }}</span>
              <span class="list-option-count">{{ r.count }}</span>
            </button>
            <span class="list-row-actions">
              <button
                v-if="memberOf.has(r.name) && covers[r.name] !== game.id"
                type="button"
                title="Use this game as the collection cover"
                @click="useAsCover(r.name)"
              >
                ★
              </button>
            </span>
          </li>
        </ul>

        <div class="popover-divider"></div>
        <div class="new-list-row">
          <input
            v-model="newName"
            type="text"
            placeholder="New collection name…"
            class="new-list-input"
            @keyup.enter="submitNew"
          />
          <button type="button" class="popover-primary-btn" @click="submitNew">
            Create
          </button>
        </div>
        <button type="button" class="manage-lists-btn" @click="goToCollections">
          Manage all collections →
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.media-extras {
  display: flex;
  align-items: center;
  gap: 8px;
}
.extras-item {
  position: relative;
}
.icon-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-text) 12%, transparent);
  color: var(--ui-text);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  position: relative;
}
.icon-btn:hover {
  border-color: color-mix(in srgb, var(--ui-accent) 40%, transparent);
}
.icon-btn.active {
  color: var(--ui-accent-text);
  border-color: color-mix(in srgb, var(--ui-accent) 40%, transparent);
  background: color-mix(in srgb, var(--ui-accent) 16%, transparent);
}
.badge-count {
  position: absolute;
  top: -4px;
  right: -4px;
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font-size: 0.6rem;
  font-weight: var(--ui-weight-title);
  border-radius: 999px;
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.pop-enter-active,
.pop-leave-active {
  transition:
    opacity 0.12s ease,
    transform 0.12s ease;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.popover {
  position: fixed;
  z-index: var(--ui-z-popover);
  width: 280px;
  max-width: calc(100vw - 32px);
  box-sizing: border-box;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-dialog);
  padding: 14px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
}
.popover-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.popover-icon {
  color: var(--ui-accent-text);
  flex-shrink: 0;
}
.popover-title {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--ui-text);
}
.popover-divider {
  height: 1px;
  background: var(--ui-surface-2);
  margin: 10px 0;
}
.popover-primary-btn {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 7px 12px;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
}
.popover-primary-btn:hover {
  filter: brightness(1.08);
}
.list-options {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 220px;
  overflow-y: auto;
}
.list-row {
  position: relative;
  display: flex;
  align-items: center;
}
.list-row-actions {
  display: flex;
  gap: 2px;
  margin-left: 2px;
  opacity: 0;
  transition: opacity 0.12s ease;
}
.list-row:hover .list-row-actions,
.list-row:focus-within .list-row-actions {
  opacity: 1;
}
@media (hover: none) {
  .list-row-actions {
    opacity: 1;
  }
}
.list-row-actions button {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: none;
  background: none;
  color: var(--ui-dim);
  font-size: 0.78rem;
  cursor: pointer;
}
.list-row-actions button:hover {
  background: color-mix(in srgb, var(--ui-text) 8%, transparent);
  color: var(--ui-accent-text);
}
.list-option {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  color: var(--ui-text);
  padding: 8px 7px;
  border-radius: var(--ui-radius-control);
  cursor: pointer;
  font-size: 0.82rem;
  font-family: inherit;
}
.list-option:hover {
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
}
.list-option:disabled {
  opacity: 0.6;
  cursor: default;
}
.list-check {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  border: 1.5px solid var(--ui-border-strong);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--ui-on-accent);
}
.list-option.checked .list-check {
  background: var(--ui-accent);
  border-color: var(--ui-accent-text);
}
.list-option-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.list-option-count {
  color: var(--ui-faint);
  font-size: 0.72rem;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.empty-hint {
  color: var(--ui-faint);
  font-size: 0.78rem;
  margin: 4px 0;
}
.new-list-row {
  display: flex;
  gap: 6px;
}
.new-list-input {
  flex: 1;
  min-width: 0;
  background: var(--ui-bg);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 7px 9px;
  font-size: 0.78rem;
  font-family: inherit;
}
.new-list-input:focus {
  outline: none;
  border-color: color-mix(in srgb, var(--ui-accent) 50%, transparent);
}
.extras-error {
  color: var(--ui-error);
  font-size: 0.76rem;
  margin: 4px 0;
}
.manage-lists-btn {
  display: block;
  width: 100%;
  text-align: center;
  background: none;
  border: none;
  color: var(--ui-accent-text);
  padding: 10px 0 0;
  margin-top: 8px;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
}
.manage-lists-btn:hover {
  color: #eaa752;
}
</style>
