<script setup lang="ts">
// Showcase: a shelf you arrange yourself with the games you are proudest of,
// each showing its rarest unlock with the real icon. Edit lets you name it,
// drag the covers into order, and add or remove games. What is on it is saved
// in the widget's own settings, with the rest of the Home layout.
import { computed, inject, ref } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import TrophyIcon from "../../TrophyIcon.vue";
import { WIDGET_CONTEXT } from "../../../home/context";
import { CHROME_KEY } from "../../../home/chrome";
import { homeData, titlesByKind } from "../../../home/data";
import type { HomeTitle } from "../../../home/data";
import { sampleTitles } from "../../../home/samples";
import { formatPercent } from "../../../utils/achievements";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();
const ctx = inject(WIDGET_CONTEXT, null);
const chrome = inject(CHROME_KEY, null);

const TITLE = "Proudest 100%s";
const MAX = 24;

const ids = computed<string[]>(() =>
  Array.isArray(props.settings.games)
    ? (props.settings.games as unknown[]).filter(
        (v): v is string => typeof v === "string",
      )
    : [],
);
const byId = computed(
  () => new Map(titlesByKind.value.game.map((t) => [t.id, t])),
);
// a game deleted from the library just drops off the shelf
const items = computed<HomeTitle[]>(() =>
  props.sample
    ? sampleTitles(5, ["game"])
    : ids.value
        .map((id) => byId.value.get(id))
        .filter((t): t is HomeTitle => !!t),
);
const rarest = (t: HomeTitle) =>
  props.sample ? null : (homeData.achSummary.value[t.id]?.rarest ?? null);

const canEdit = computed(() => !props.sample && !!ctx?.value);
const editing = ref(false);

function save(next: string[]) {
  ctx?.value?.update({ games: next.slice(0, MAX) });
}
function remove(id: string) {
  save(ids.value.filter((g) => g !== id));
}

// ---- name ----
const name = computed(() => chrome?.value.heading.trim() || TITLE);
function rename(e: Event) {
  const value = (e.target as HTMLInputElement).value.trim();
  ctx?.value?.update({ _heading: value === TITLE ? "" : value.slice(0, 60) });
}

// ---- adding ----
const query = ref("");
const matches = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (q.length < 2) return [];
  const on = new Set(ids.value);
  return titlesByKind.value.game
    .filter((t) => !on.has(t.id) && t.title.toLowerCase().includes(q))
    .slice(0, 8);
});
function add(t: HomeTitle) {
  save([...ids.value, t.id]);
  query.value = "";
}
// every 100% game not already on it, rarest first
const finished = computed(() => {
  const on = new Set(ids.value);
  const summary = homeData.achSummary.value;
  return titlesByKind.value.game
    .filter((t) => {
      const s = summary[t.id];
      return !on.has(t.id) && !!s && s.total > 0 && s.unlocked >= s.total;
    })
    .sort(
      (a, b) =>
        (summary[a.id]?.rarest?.percent ?? 101) -
        (summary[b.id]?.rarest?.percent ?? 101),
    );
});
function addFinished() {
  save([...ids.value, ...finished.value.map((t) => t.id)]);
}

// ---- dragging into order ----
const dragFrom = ref<number | null>(null);
const dragOver = ref<number | null>(null);
function onDragStart(i: number, e: DragEvent) {
  dragFrom.value = i;
  e.dataTransfer?.setData("text/plain", String(i));
  if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
}
function onDrop(i: number) {
  const from = dragFrom.value;
  dragFrom.value = null;
  dragOver.value = null;
  if (from === null || from === i) return;
  const next = [...items.value.map((t) => t.id)];
  const [moved] = next.splice(from, 1);
  next.splice(i, 0, moved);
  save(next);
}
function onDragEnd() {
  dragFrom.value = null;
  dragOver.value = null;
}
// the same moves without a mouse
function nudge(i: number, by: -1 | 1) {
  const j = i + by;
  if (j < 0 || j >= items.value.length) return;
  const next = items.value.map((t) => t.id);
  [next[i], next[j]] = [next[j], next[i]];
  save(next);
}
</script>

<template>
  <WidgetFrame :title="TITLE" :sample="sample">
    <template #actions>
      <span class="count"
        >{{ items.length }} {{ items.length === 1 ? "game" : "games" }}</span
      >
      <button
        v-if="canEdit"
        type="button"
        class="btn"
        :class="{ pri: editing }"
        @click="editing = !editing"
      >
        {{ editing ? "Done" : "Edit" }}
      </button>
    </template>

    <div class="sc-body">
      <div v-if="editing" class="edit-bar">
        <input
          class="name-field"
          :value="name"
          maxlength="60"
          aria-label="Showcase name"
          @change="rename"
        />
        <span class="edit-note">Drag covers to reorder</span>
        <button
          v-if="finished.length"
          type="button"
          class="btn"
          @click="addFinished"
        >
          Add my {{ finished.length }} other 100%
          {{ finished.length === 1 ? "game" : "games" }}
        </button>
      </div>

      <div v-if="items.length || editing" class="sc" :class="{ editing }">
        <div
          v-for="(t, i) in items"
          :key="t.id"
          class="slot"
          :class="{
            lifted: dragFrom === i,
            over: dragOver === i && dragFrom !== i,
          }"
          :draggable="editing"
          @dragstart="onDragStart(i, $event)"
          @dragover.prevent="dragOver = i"
          @dragleave="dragOver === i && (dragOver = null)"
          @drop.prevent="onDrop(i)"
          @dragend="onDragEnd"
        >
          <component
            :is="editing || sample ? 'div' : 'router-link'"
            :to="editing || sample ? undefined : t.to"
            class="cv"
          >
            <img v-if="t.art" :src="t.art" alt="" loading="lazy" />
            <span v-else class="cv-blank">{{ t.title }}</span>
          </component>
          <template v-if="editing">
            <span class="tool l" title="Drag to move" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path
                  d="M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01"
                />
              </svg>
            </span>
            <button
              type="button"
              class="tool r"
              :aria-label="`Take ${t.title} off`"
              title="Take it off"
              @click="remove(t.id)"
            >
              <svg viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
            <span class="moves">
              <button
                type="button"
                :disabled="i === 0"
                :aria-label="`Move ${t.title} earlier`"
                @click="nudge(i, -1)"
              >
                &#8249;
              </button>
              <button
                type="button"
                :disabled="i === items.length - 1"
                :aria-label="`Move ${t.title} later`"
                @click="nudge(i, 1)"
              >
                &#8250;
              </button>
            </span>
          </template>
          <div class="cap">
            <b>{{ t.title }}</b>
          </div>
          <div v-if="rarest(t)" class="rare">
            <img
              v-if="rarest(t)?.icon_url"
              :src="rarest(t)?.icon_url ?? ''"
              alt=""
            />
            <span v-else class="rare-blank"><TrophyIcon /></span>
            <span>{{ rarest(t)?.name }}</span>
            <b>{{ formatPercent(rarest(t)?.percent ?? 0) }}</b>
          </div>
        </div>

        <div v-if="editing && items.length < MAX" class="add">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 5v14M5 12h14" />
          </svg>
          <span>Add a game</span>
          <input
            v-model="query"
            class="add-field"
            type="search"
            placeholder="Search games"
            aria-label="Find a game to add"
          />
          <div v-if="matches.length" class="matches">
            <button
              v-for="m in matches"
              :key="m.id"
              type="button"
              class="match"
              @click="add(m)"
            >
              <img v-if="m.art" :src="m.art" alt="" />
              <span>{{ m.title }}</span>
            </button>
          </div>
        </div>
      </div>

      <div v-else class="empty">
        <TrophyIcon />
        <p>Put the games you are proudest of here, in your own order.</p>
        <div class="empty-btns">
          <button
            v-if="canEdit && finished.length"
            type="button"
            class="btn pri"
            @click="addFinished"
          >
            Add my {{ finished.length }} 100%
            {{ finished.length === 1 ? "game" : "games" }}
          </button>
          <button
            v-if="canEdit"
            type="button"
            class="btn"
            @click="editing = true"
          >
            Pick games
          </button>
        </div>
      </div>
    </div>
  </WidgetFrame>
</template>

<style scoped>
.count {
  color: var(--ui-dim-2);
  font-size: 13px;
}
.btn {
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  border-radius: 8px;
  padding: 5px 12px;
  border: 1px solid var(--ui-border-strong);
  background: var(--ui-surface-2);
  color: var(--ui-text-soft);
  cursor: pointer;
}
.btn:hover {
  color: var(--ui-heading);
  border-color: var(--ui-border-hover, var(--ui-border-strong));
}
.btn.pri {
  background: var(--ui-accent);
  border-color: var(--ui-accent);
  color: var(--ui-on-accent);
}
.sc-body {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
}

.edit-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
}
.name-field {
  flex: 0 1 320px;
  min-width: 0;
  font: inherit;
  font-size: 15px;
  font-weight: 700;
  color: var(--ui-heading);
  background: var(--ui-surface-2);
  border: 1px solid var(--ui-border-strong);
  border-radius: 8px;
  padding: 8px 12px;
}
.edit-note {
  color: var(--ui-dim-2);
  font-size: 13px;
}
.edit-bar .btn {
  margin-left: auto;
}

.sc {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 20px 18px;
}
.slot {
  position: relative;
  min-width: 0;
}
.cv {
  position: relative;
  display: block;
  aspect-ratio: 2 / 3;
  border-radius: 6px;
  overflow: hidden;
  background: var(--ui-surface-2);
  transition:
    transform 0.2s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.2s ease;
}
a.cv:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 26px rgba(0, 0, 0, 0.5);
}
.cv img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.cv-blank {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  padding: 10px;
  font-size: 12px;
  font-weight: 700;
  color: var(--ui-text-soft);
}
.editing .cv {
  cursor: grab;
}
.lifted .cv {
  transform: translateY(-6px) rotate(-2deg);
  box-shadow: 0 16px 30px rgba(0, 0, 0, 0.6);
  outline: 2px solid var(--ui-accent);
  outline-offset: 2px;
}
.over .cv {
  outline: 2px dashed var(--ui-accent);
  outline-offset: 2px;
}
.tool {
  position: absolute;
  top: 6px;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 0;
  padding: 0;
  background: rgba(12, 12, 12, 0.8);
  color: #e5e5e5;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}
.tool.l {
  left: 6px;
  cursor: grab;
}
.tool.r {
  right: 6px;
  cursor: pointer;
}
.tool.r:hover {
  background: color-mix(in srgb, var(--ui-danger) 80%, transparent);
}
.tool svg,
.add svg {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}
/* move buttons for the keyboard; they show on focus or hover */
.moves {
  position: absolute;
  left: 6px;
  right: 6px;
  top: 40px;
  display: flex;
  justify-content: space-between;
  opacity: 0;
  transition: opacity 0.15s ease;
  z-index: 2;
}
.slot:hover .moves,
.moves:focus-within {
  opacity: 1;
}
.moves button {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 0;
  background: rgba(12, 12, 12, 0.8);
  color: #e5e5e5;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}
.moves button:disabled {
  opacity: 0.35;
  cursor: default;
}

.cap {
  margin-top: 8px;
  min-width: 0;
}
.cap b {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--ui-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rare {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--ui-dim-2);
  min-width: 0;
}
.rare img,
.rare-blank {
  width: 22px;
  height: 22px;
  border-radius: 3px;
  flex: 0 0 auto;
  object-fit: cover;
  box-shadow: 0 0 0 1px rgba(241, 205, 106, 0.7);
}
.rare-blank {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #f1cd6a;
  background: var(--ui-surface-2);
}
.rare-blank :deep(svg) {
  width: 12px;
  height: 12px;
}
.rare span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rare b {
  color: #e9be5a;
  font-weight: 700;
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}

.add {
  position: relative;
  aspect-ratio: 2 / 3;
  border-radius: 6px;
  border: 1px dashed var(--ui-border-strong);
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  justify-content: center;
  padding: 10px;
  box-sizing: border-box;
  color: var(--ui-dim-2);
  font-size: 12.5px;
  font-weight: 600;
}
.add-field {
  width: 100%;
  box-sizing: border-box;
  font: inherit;
  font-size: 12px;
  font-weight: 500;
  color: var(--ui-text);
  background: var(--ui-surface-2);
  border: 1px solid var(--ui-border);
  border-radius: 6px;
  padding: 6px 8px;
}
.matches {
  position: absolute;
  left: 0;
  top: calc(100% + 6px);
  width: max(100%, 240px);
  z-index: 5;
  display: flex;
  flex-direction: column;
  background: var(--ui-popover);
  border: 1px solid var(--ui-border-strong);
  border-radius: 8px;
  padding: 4px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5);
}
.match {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 0;
  border-radius: 6px;
  background: none;
  color: var(--ui-text-soft);
  font: inherit;
  font-size: 12.5px;
  text-align: left;
  padding: 5px 6px;
  cursor: pointer;
}
.match:hover {
  background: color-mix(in srgb, var(--ui-wash-base) 7%, transparent);
  color: var(--ui-heading);
}
.match img {
  width: 20px;
  height: 30px;
  border-radius: 3px;
  object-fit: cover;
  flex: 0 0 auto;
}
.match span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty {
  height: 100%;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-align: center;
  color: var(--ui-dim-2);
}
.empty > :deep(svg) {
  width: 26px;
  height: 26px;
  color: #e9be5a;
}
.empty p {
  margin: 0;
  font-size: 13.5px;
}
.empty-btns {
  display: flex;
  gap: 8px;
}
@media (prefers-reduced-motion: reduce) {
  .cv,
  .moves {
    transition: none;
  }
}
</style>
