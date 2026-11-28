<script setup lang="ts">
// Edit the tabs across the top of the games library: make your own, pick which
// statuses each one shows (All and Library too), and hide built-in ones you
// never use. Tabs are moved by dragging them on the tab bar, or with the arrows.
import { computed, ref } from "vue";
import SmartRulesEditor from "./SmartRulesEditor.vue";
import StatusShowPicker from "./StatusShowPicker.vue";
import {
  addCustomTab,
  allTabStatuses,
  allTabs,
  claimedByTab,
  matchesCustomTab,
  moveTab,
  placeTab,
  removeCustomTab,
  setAllTabStatuses,
  setTabHidden,
  updateCustomTab,
  type CustomGameTab,
} from "../state/gameTabs";
import { describeSmartCollection, statusesOf } from "../state/smartCollections";
import type { SmartCondition, SmartMatch } from "../state/smartCollections";
import { preferences } from "../state/preferences";
import { queuePreferences } from "../services/preferences";
import { rowsToConditions, STATUS_OPTIONS } from "../utils/smartRuleFields";
import type { RuleRow } from "../utils/smartRuleFields";
import { useConfirm } from "../state/dialog";
import type { Game, GameStatus } from "../types/game";
import { isSetAside } from "../utils/gameOrganize";

const props = defineProps<{
  tagOptions: string[];
  sourceOptions: string[];
  collectionOptions: string[];
  // every game in the library, for the live count while you edit
  games: Game[];
}>();
const emit = defineEmits<{ close: [] }>();
const confirm = useConfirm();

const EVERY: GameStatus[] = [...STATUS_OPTIONS];
const LABEL: Record<GameStatus, string> = {
  playing: "Playing",
  beaten: "Beaten",
  mastered: "Mastered",
  played: "Played",
  "on hold": "On hold",
  dropped: "Dropped",
  backlog: "Backlog",
  wishlist: "Wishlist",
};
// "Shows every status" or "Not shown: Backlog, Wishlist"
function statusNote(statuses: GameStatus[] | null | undefined): string {
  const off = EVERY.filter((s) => statuses && !statuses.includes(s));
  if (!off.length) return "Shows every status";
  if (off.length === EVERY.length) return "Shows nothing";
  const on = EVERY.filter((s) => !off.includes(s));
  // whichever list is shorter reads better
  return on.length < off.length
    ? `Shows: ${on.map((s) => LABEL[s]).join(", ")}`
    : `Not shown: ${off.map((s) => LABEL[s]).join(", ")}`;
}

// ---- the list ----
const tabs = computed(() => allTabs.value);
// built-in tabs whose statuses you can pick; the others are one status each
type Pickable = "all" | "library";
const isPickable = (id: string): id is Pickable =>
  id === "all" || id === "library";
function builtInStatuses(id: Pickable): GameStatus[] {
  return id === "all"
    ? (allTabStatuses.value ?? EVERY)
    : preferences.value.library_statuses_game;
}
function describe(tab: CustomGameTab): string {
  const parts: string[] = [];
  if (isMine(tab)) parts.push("Games you put in it");
  else if (tab.rules.length)
    parts.push(
      describeSmartCollection({
        id: tab.id,
        name: tab.name,
        ...tab.rules[0],
        rules: tab.rules,
        match: tab.match,
      }),
    );
  if (tab.statuses || !parts.length) parts.push(statusNote(tab.statuses));
  if (tab.hideElsewhere) parts.push("only shown here");
  return parts.join(" · ");
}
async function remove(tab: CustomGameTab) {
  const ok = await confirm({
    title: `Delete the "${tab.name}" tab?`,
    message:
      "Only the tab goes. Its games stay in your library, and a collection it used is kept.",
    confirmLabel: "Delete tab",
    danger: true,
  });
  if (ok) removeCustomTab(tab.id);
}

// dragging a row to move the tab, the same as dragging it on the tab bar
const dragId = ref<string | null>(null);
const dropAt = ref<{ id: string; after: boolean } | null>(null);
function rowDragStart(e: DragEvent, id: string) {
  dragId.value = id;
  e.dataTransfer?.setData("text/plain", id);
  if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
}
function rowDragOver(e: DragEvent, id: string) {
  if (!dragId.value) return;
  e.preventDefault();
  const box = (e.currentTarget as HTMLElement).getBoundingClientRect();
  dropAt.value = { id, after: e.clientY > box.top + box.height / 2 };
}
function rowDrop(id: string) {
  if (dragId.value && dropAt.value?.id === id)
    placeTab(dragId.value, id, dropAt.value.after);
  rowDragEnd();
}
function rowDragEnd() {
  dragId.value = null;
  dropAt.value = null;
}

// ---- making or changing one ----
type Kind = "mine" | "rules";
const editing = ref<CustomGameTab | "new" | Pickable | null>(null);
const name = ref("");
const kind = ref<Kind>("mine");
const statuses = ref<GameStatus[]>([...EVERY]);
const rows = ref<RuleRow[]>([]);
const match = ref<SmartMatch>("all");
const hideElsewhere = ref(false);
const error = ref<string | null>(null);
const saving = ref(false);

const editingBuiltIn = computed<Pickable | null>(() =>
  editing.value === "all" || editing.value === "library" ? editing.value : null,
);
const editingTab = computed<CustomGameTab | null>(() =>
  editing.value && typeof editing.value === "object" ? editing.value : null,
);
const heading = computed(() => {
  if (editing.value === "new") return "New tab";
  if (editing.value === "all") return "Edit All";
  if (editing.value === "library") return "Edit Library";
  return editingTab.value ? `Edit "${editingTab.value.name}"` : "";
});

// a tab of games you put there yourself is a rule "In collection <its name>"
function isMine(tab: CustomGameTab): boolean {
  return (
    tab.rules.length === 1 &&
    tab.rules[0].field === "collection" &&
    tab.rules[0].value.toLowerCase() === tab.name.toLowerCase()
  );
}
// a new tab of games you put there is usually a pile to keep out of the way;
// a tab that matches is usually a view over games that belong elsewhere too
function pickKind(next: Kind) {
  if (editing.value === "new" && kind.value !== next)
    hideElsewhere.value = next === "mine";
  kind.value = next;
}
function startNew() {
  editing.value = "new";
  name.value = "";
  kind.value = "mine";
  statuses.value = [...EVERY];
  rows.value = [];
  match.value = "all";
  hideElsewhere.value = true;
  error.value = null;
}
function startBuiltIn(id: Pickable) {
  editing.value = id;
  statuses.value = [...builtInStatuses(id)];
  error.value = null;
}
function openRow(id: string, tab: CustomGameTab | null) {
  if (tab) startEdit(tab);
  else if (isPickable(id)) startBuiltIn(id);
}
function startEdit(tab: CustomGameTab) {
  editing.value = tab;
  name.value = tab.name;
  kind.value = isMine(tab) ? "mine" : "rules";
  // a status rule from before tabs had their own status buttons moves onto them
  let shown: GameStatus[] = tab.statuses ? [...tab.statuses] : [...EVERY];
  const rest: SmartCondition[] = [];
  for (const r of isMine(tab) ? [] : tab.rules) {
    if (
      r.field === "status" &&
      (tab.match === "all" || tab.rules.length === 1)
    ) {
      const named = statusesOf(r.value);
      shown = shown.filter((s) =>
        r.not ? !named.includes(s) : named.includes(s),
      );
    } else rest.push(r);
  }
  statuses.value = shown;
  rows.value = rest.map((r) => ({ ...r }));
  match.value = tab.match;
  hideElsewhere.value = tab.hideElsewhere;
  error.value = null;
}

// the tab being edited as it would be saved, or what is missing from it
const draft = computed<CustomGameTab | string>(() => {
  const trimmed = name.value.trim();
  let rules: SmartCondition[] = [];
  if (kind.value === "mine") {
    if (!trimmed) return "Name the tab to see which games are in it.";
    rules = [{ field: "collection", value: trimmed }];
  } else if (rows.value.length) {
    const found = rowsToConditions(rows.value);
    if (typeof found === "string") return found;
    rules = found;
  }
  return {
    id: editingTab.value?.id ?? "draft",
    name: trimmed,
    statuses:
      statuses.value.length === EVERY.length ? undefined : statuses.value,
    rules,
    match: match.value,
    hideElsewhere: hideElsewhere.value,
  };
});

// what the tab would hold right now, worked out the way the library does it
const preview = computed<Game[] | string>(() => {
  const visible = props.games.filter((g) => !isSetAside(g));
  if (editingBuiltIn.value) {
    return visible.filter(
      (g) => !claimedByTab(g) && statuses.value.includes(g.status),
    );
  }
  const tab = draft.value;
  if (typeof tab === "string") return tab;
  return visible.filter((g) => {
    if (!matchesCustomTab(g, tab)) return false;
    if (tab.hideElsewhere) return true;
    const claim = claimedByTab(g);
    return !claim || claim.id === tab.id;
  });
});
const previewTitles = computed(() =>
  typeof preview.value === "string"
    ? []
    : preview.value
        .map((g) => g.title)
        .sort((a, b) => a.localeCompare(b))
        .slice(0, 8),
);

async function saveBuiltIn(id: Pickable) {
  if (id === "all") {
    setAllTabStatuses(
      statuses.value.length === EVERY.length ? null : statuses.value,
    );
    return true;
  }
  saving.value = true;
  const before = preferences.value;
  try {
    const { prefs } = await queuePreferences({
      library_statuses_game: statuses.value,
    });
    preferences.value = { ...preferences.value, ...prefs };
    return true;
  } catch (e) {
    preferences.value = before;
    error.value = e instanceof Error ? e.message : "Could not save.";
    return false;
  } finally {
    saving.value = false;
  }
}

async function save() {
  error.value = null;
  if (!statuses.value.length) {
    error.value = "Turn on at least one status.";
    return;
  }
  if (editingBuiltIn.value) {
    if (await saveBuiltIn(editingBuiltIn.value)) editing.value = null;
    return;
  }
  const trimmed = name.value.trim();
  if (!trimmed) {
    error.value = "Give the tab a name.";
    return;
  }
  const clash = tabs.value.find(
    (t) =>
      t.label.toLowerCase() === trimmed.toLowerCase() &&
      (!editingTab.value || t.custom?.id !== editingTab.value.id),
  );
  if (clash) {
    error.value = `There is already a "${clash.label}" tab.`;
    return;
  }
  const tab = draft.value;
  if (typeof tab === "string") {
    error.value = tab;
    return;
  }
  const fields = {
    name: tab.name,
    statuses: tab.statuses,
    rules: tab.rules,
    match: tab.match,
    hideElsewhere: tab.hideElsewhere,
  };
  if (editingTab.value) updateCustomTab(editingTab.value.id, fields);
  else addCustomTab(fields);
  editing.value = null;
}
</script>

<template>
  <div class="ui-backdrop tabs-backdrop" @click.self="emit('close')">
    <div
      class="tabs-modal"
      role="dialog"
      aria-modal="true"
      aria-label="Edit tabs"
      @keydown.esc="editing ? (editing = null) : emit('close')"
    >
      <template v-if="!editing">
        <div class="head">
          <h3>Tabs</h3>
          <p class="lead">
            Pick what each tab shows, make your own, and hide the ones you never
            use. Drag a row (or a tab on the tab bar) to move it.
          </p>
        </div>
        <ul class="tab-list">
          <li
            v-for="(t, i) in tabs"
            :key="t.id"
            class="tab-row"
            :class="{
              off: t.hidden,
              dragging: dragId === t.id,
              'drop-above': dropAt?.id === t.id && !dropAt.after,
              'drop-below': dropAt?.id === t.id && dropAt.after,
            }"
            @dragover="rowDragOver($event, t.id)"
            @drop.prevent="rowDrop(t.id)"
          >
            <span
              class="grip"
              draggable="true"
              title="Drag to move"
              aria-hidden="true"
              @dragstart="rowDragStart($event, t.id)"
              @dragend="rowDragEnd"
            >
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                aria-hidden="true"
              >
                <circle cx="9" cy="6" r="1.6" fill="currentColor" />
                <circle cx="15" cy="6" r="1.6" fill="currentColor" />
                <circle cx="9" cy="12" r="1.6" fill="currentColor" />
                <circle cx="15" cy="12" r="1.6" fill="currentColor" />
                <circle cx="9" cy="18" r="1.6" fill="currentColor" />
                <circle cx="15" cy="18" r="1.6" fill="currentColor" />
              </svg>
            </span>
            <span class="moves">
              <button
                type="button"
                :disabled="i === 0"
                :aria-label="`Move ${t.label} up`"
                @click="moveTab(t.id, -1)"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="12"
                  height="12"
                  aria-hidden="true"
                >
                  <path
                    d="M6 15l6-6 6 6"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.4"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </button>
              <button
                type="button"
                :disabled="i === tabs.length - 1"
                :aria-label="`Move ${t.label} down`"
                @click="moveTab(t.id, 1)"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="12"
                  height="12"
                  aria-hidden="true"
                >
                  <path
                    d="M6 9l6 6 6-6"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.4"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </button>
            </span>
            <button
              v-if="t.custom || isPickable(t.id)"
              type="button"
              class="tab-text"
              @click="openRow(t.id, t.custom)"
            >
              <b
                >{{ t.label }}<em v-if="t.custom" class="tag">Yours</em
                ><em v-if="t.hidden" class="tag dim">Hidden</em></b
              >
              <small>{{
                t.custom
                  ? describe(t.custom)
                  : statusNote(builtInStatuses(t.id as Pickable))
              }}</small>
            </button>
            <span v-else class="tab-text">
              <b
                >{{ t.label }}<em v-if="t.hidden" class="tag dim">Hidden</em></b
              >
              <small>{{
                t.id === "set aside"
                  ? "Games you set aside"
                  : `Your ${t.label.toLowerCase()} games`
              }}</small>
            </span>
            <span class="row-actions">
              <button
                v-if="t.custom || isPickable(t.id)"
                type="button"
                class="icon-btn"
                :title="`Edit ${t.label}`"
                :aria-label="`Edit ${t.label}`"
                @click="openRow(t.id, t.custom)"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="15"
                  height="15"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
                </svg>
              </button>
              <button
                v-if="t.custom"
                type="button"
                class="icon-btn danger"
                :title="`Delete ${t.label}`"
                :aria-label="`Delete ${t.label}`"
                @click="remove(t.custom)"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="15"
                  height="15"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M3 6h18" />
                  <path d="M8 6V4h8v2" />
                  <path d="M19 6l-1 14H6L5 6" />
                </svg>
              </button>
              <button
                v-if="!t.custom && t.id !== 'all'"
                type="button"
                class="icon-btn"
                :class="{ on: !t.hidden }"
                :aria-pressed="!t.hidden"
                :title="t.hidden ? `Show ${t.label}` : `Hide ${t.label}`"
                :aria-label="t.hidden ? `Show ${t.label}` : `Hide ${t.label}`"
                @click="setTabHidden(t.id, !t.hidden)"
              >
                <svg
                  v-if="!t.hidden"
                  viewBox="0 0 24 24"
                  width="16"
                  height="16"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg
                  v-else
                  viewBox="0 0 24 24"
                  width="16"
                  height="16"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M3 3l18 18" />
                  <path
                    d="M10.6 5.1A10.6 10.6 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.2 4.1M6.6 6.6C3.8 8.4 2 12 2 12s3.5 7 10 7a9.7 9.7 0 0 0 5.4-1.6"
                  />
                  <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
                </svg>
              </button>
            </span>
          </li>
        </ul>
        <div class="actions">
          <button
            type="button"
            class="ui-btn ui-btn-secondary"
            @click="startNew"
          >
            + New tab
          </button>
          <span class="grow"></span>
          <button
            type="button"
            class="ui-btn ui-btn-primary"
            @click="emit('close')"
          >
            Done
          </button>
        </div>
      </template>

      <template v-else>
        <h3>{{ heading }}</h3>
        <p v-if="editingBuiltIn === 'all'" class="lead">
          Everything you have, apart from set-aside games and games a tab keeps
          to itself. Turn off what you do not want in it.
        </p>
        <p v-else-if="editingBuiltIn === 'library'" class="lead">
          The games you own and care about. Turn off what you do not want in it.
          This is the same choice as in Settings, Tabs and adding.
        </p>
        <template v-if="!editingBuiltIn">
          <label class="field">
            <span>Name</span>
            <input
              v-model="name"
              class="ui-field"
              maxlength="40"
              placeholder="e.g. Online, Books, Test servers, Short games"
            />
          </label>
          <div class="kind-pick">
            <button
              type="button"
              :class="{ active: kind === 'mine' }"
              @click="pickKind('mine')"
            >
              <strong>Games I put in it</strong>
              <span
                >Add games with Add to Collection; the tab uses a collection
                with its name</span
              >
            </button>
            <button
              type="button"
              :class="{ active: kind === 'rules' }"
              @click="pickKind('rules')"
            >
              <strong>Games that match</strong>
              <span>By status, and tag, platform, playtime and more</span>
            </button>
          </div>
        </template>
        <StatusShowPicker v-model="statuses" />
        <SmartRulesEditor
          v-if="!editingBuiltIn && kind === 'rules'"
          v-model:match="match"
          v-model:rows="rows"
          :tag-options="props.tagOptions"
          :source-options="props.sourceOptions"
          :collection-options="props.collectionOptions"
          :hide-fields="['status']"
          optional
          id-prefix="game-tab"
        />
        <div class="preview" aria-live="polite">
          <template v-if="typeof preview === 'string'">{{ preview }}</template>
          <template v-else-if="preview.length === 0">
            {{
              !editingBuiltIn && kind === "mine"
                ? `No games in a "${name.trim()}" collection with these statuses yet.`
                : "No games would show here."
            }}
          </template>
          <template v-else>
            <b
              >{{ preview.length }}
              {{ preview.length === 1 ? "game" : "games" }}</b
            >
            <span
              >{{ previewTitles.join(", ")
              }}{{
                preview.length > previewTitles.length
                  ? `, and ${preview.length - previewTitles.length} more`
                  : ""
              }}</span
            >
          </template>
        </div>
        <label v-if="!editingBuiltIn" class="hide-row">
          <input v-model="hideElsewhere" type="checkbox" />
          <span>
            <b>Only show these games here</b>
            <small
              >Keeps them out of All, Library, Backlog and your other tabs, so
              they stop crowding them</small
            >
          </span>
        </label>
        <p v-if="error" class="ui-error-box">{{ error }}</p>
        <div class="actions">
          <button
            type="button"
            class="ui-btn ui-btn-secondary"
            @click="editing = null"
          >
            Back
          </button>
          <span class="grow"></span>
          <button
            type="button"
            class="ui-btn ui-btn-primary"
            :disabled="saving || !statuses.length"
            @click="save"
          >
            {{ editing === "new" ? "Make tab" : saving ? "Saving…" : "Save" }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.tabs-modal {
  width: min(560px, calc(100vw - 32px));
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  overscroll-behavior: contain;
  box-sizing: border-box;
  background: var(--ui-popover);
  border: 1px solid var(--ui-border-strong);
  border-radius: 14px;
  padding: 20px 20px 0;
  box-shadow: 0 24px 60px
    color-mix(in srgb, var(--ui-scrim-base) 55%, transparent);
}
h3 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--ui-heading);
}
.lead {
  margin: 6px 0 14px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--ui-dim);
}
/* the title stays put while the list scrolls under it */
.head {
  position: sticky;
  top: -20px;
  z-index: 2;
  margin: -20px -20px 0;
  padding: 20px 20px 2px;
  background: var(--ui-popover);
}
.tab-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.tab-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 6px 6px 4px;
  border: 1px solid var(--ui-border);
  border-radius: 10px;
  background: var(--ui-surface);
}
.tab-row:hover {
  border-color: var(--ui-border-strong);
}
.tab-row.dragging {
  opacity: 0.4;
}
.tab-row.drop-above::before,
.tab-row.drop-below::after {
  content: "";
  position: absolute;
  left: 6px;
  right: 6px;
  height: 2px;
  border-radius: 2px;
  background: var(--ui-accent);
}
.tab-row.drop-above::before {
  top: -4px;
}
.tab-row.drop-below::after {
  bottom: -4px;
}
.tab-row.off .tab-text {
  opacity: 0.55;
}
.grip {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 30px;
  color: var(--ui-dim-2);
  cursor: grab;
}
.grip:active {
  cursor: grabbing;
}
.moves {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.moves button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 16px;
  padding: 0;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--ui-dim);
  cursor: pointer;
}
.moves button:hover:not(:disabled) {
  background: var(--ui-surface-2);
  color: var(--ui-heading);
}
.moves button:disabled {
  opacity: 0.25;
  cursor: default;
}
.tab-text {
  flex: 1;
  min-width: 0;
  padding: 4px 6px;
  text-align: left;
}
button.tab-text {
  border: 0;
  border-radius: 8px;
  background: transparent;
  font: inherit;
  cursor: pointer;
}
button.tab-text:hover b {
  color: var(--ui-accent);
}
.tab-text b {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  color: var(--ui-heading);
}
.tab-text small {
  display: block;
  margin-top: 1px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--ui-dim-2);
}
.tag {
  padding: 1px 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--ui-accent) 16%, transparent);
  color: var(--ui-accent);
  font-size: 10.5px;
  font-style: normal;
  font-weight: 600;
}
.tag.dim {
  background: var(--ui-surface-2);
  color: var(--ui-dim);
}
.row-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}
.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--ui-dim-2);
  cursor: pointer;
}
.icon-btn:hover {
  background: var(--ui-surface-2);
  color: var(--ui-heading);
}
.icon-btn.on {
  color: var(--ui-text-soft);
}
.icon-btn.danger:hover {
  color: var(--ui-danger);
}
.hide-row input {
  accent-color: var(--ui-accent);
}
/* the buttons stay at the bottom while the list scrolls */
.actions {
  position: sticky;
  bottom: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px -20px 0;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--ui-border);
  background: var(--ui-popover);
}
.grow {
  flex: 1;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 14px 0;
  font-size: 0.82rem;
  color: var(--ui-text-soft);
}
.kind-pick {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 16px;
}
.kind-pick button {
  display: flex;
  flex-direction: column;
  gap: 3px;
  text-align: left;
  background: var(--ui-bg-2);
  border: 1px solid var(--ui-border-strong);
  border-radius: 10px;
  padding: 10px 12px;
  color: var(--ui-text-soft);
  font-family: inherit;
  cursor: pointer;
}
.kind-pick button strong {
  font-size: 0.86rem;
  color: var(--ui-heading);
}
.kind-pick button span {
  font-size: 0.72rem;
  color: var(--ui-dim);
}
.kind-pick button.active {
  border-color: var(--ui-accent);
  background: color-mix(in srgb, var(--ui-accent) 10%, transparent);
}
.preview {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--ui-surface-2);
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--ui-dim);
}
.preview b {
  color: var(--ui-heading);
  margin-right: 6px;
}
.hide-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--ui-border);
  border-radius: 10px;
  cursor: pointer;
}
.hide-row b {
  display: block;
  font-size: 13.5px;
  color: var(--ui-heading);
}
.hide-row small {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: var(--ui-dim-2);
}
@media (max-width: 520px) {
  .kind-pick {
    grid-template-columns: 1fr;
  }
  /* a sheet from the bottom on a phone, with room to reach every row */
  .tabs-backdrop {
    align-items: flex-end;
    padding: 0;
  }
  .tabs-modal {
    width: 100%;
    max-height: calc(100vh - 40px);
    border-radius: 16px 16px 0 0;
    border-bottom: 0;
  }
  .actions {
    padding-bottom: calc(16px + env(safe-area-inset-bottom));
  }
}
</style>
