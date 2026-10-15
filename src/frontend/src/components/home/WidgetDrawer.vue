<script setup lang="ts">
// The widget gallery: a list of everything you can add on the left; pick one and
// see it drawn live on the right, at the size it would have on the page, with
// every option it has. If you have nothing of that kind yet it is drawn with
// marked examples. Press Add when it looks right.
import { computed, ref } from "vue";
import SettingsFields from "./SettingsFields.vue";
import WidgetHost from "./WidgetHost.vue";
import { GRID_COLUMNS, ROW_PX } from "../../home/layout";
import { WIDGETS } from "../../home/registry";
import type { WidgetCategory, WidgetDefinition } from "../../home/registry";

const emit = defineEmits<{
  add: [
    type: string,
    variant: string | null,
    settings: Record<string, unknown>,
    size: { w: number; h: number },
  ];
  close: [];
}>();

const query = ref("");
const selectedType = ref<string | null>(null);
const draft = ref<Record<string, unknown>>({});
const variant = ref<string | null>(null);
const sizeChoice = ref<"compact" | "default" | "full">("default");

const selected = computed<WidgetDefinition | null>(
  () => WIDGETS.find((w) => w.type === selectedType.value) ?? null,
);

const grouped = computed(() => {
  const q = query.value.trim().toLowerCase();
  const order: WidgetCategory[] = [
    "Library",
    "Progress",
    "Achievements",
    "Calendar",
    "Stats",
    "Tools",
    "Layout",
  ];
  return order
    .map((category) => ({
      category,
      items: WIDGETS.filter(
        (w) =>
          w.category === category &&
          (!q ||
            `${w.name} ${w.description} ${w.category}`
              .toLowerCase()
              .includes(q)),
      ),
    }))
    .filter((g) => g.items.length);
});

function pick(def: WidgetDefinition) {
  selectedType.value = def.type;
  draft.value = { ...def.defaults };
  variant.value = def.variants[0]?.id ?? null;
  sizeChoice.value = "default";
}

const sizes = computed(() => {
  const def = selected.value;
  if (!def) return [];
  const list: {
    id: "compact" | "default" | "full";
    label: string;
    w: number;
    h: number;
  }[] = [];
  const compactW = Math.max(def.size.minW, Math.ceil(def.size.w / 2));
  if (compactW < def.size.w)
    list.push({ id: "compact", label: "Compact", w: compactW, h: def.size.h });
  list.push({ id: "default", label: "Default", w: def.size.w, h: def.size.h });
  if (def.size.w < GRID_COLUMNS)
    list.push({
      id: "full",
      label: "Full width",
      w: GRID_COLUMNS,
      h: def.size.h,
    });
  return list;
});
const size = computed(
  () => sizes.value.find((s) => s.id === sizeChoice.value) ?? sizes.value[0],
);

// drawn at 64px columns, then scaled to fit the pane
const CELL = 64;
const GAP = 16;
const PREVIEW_W = 470;
const PREVIEW_H = 330;
const stage = computed(() => {
  const s = size.value;
  if (!s) return { w: 0, h: 0, scale: 1 };
  const w = s.w * CELL + (s.w - 1) * GAP;
  const h = s.h * ROW_PX + (s.h - 1) * GAP;
  return { w, h, scale: Math.min(1, PREVIEW_W / w, PREVIEW_H / h) };
});

function onChange(settings: Record<string, unknown>, v: string | null) {
  draft.value = settings;
  variant.value = v;
}

function add() {
  const def = selected.value;
  if (!def || !size.value) return;
  emit(
    "add",
    def.type,
    variant.value,
    JSON.parse(JSON.stringify(draft.value)),
    {
      w: size.value.w,
      h: size.value.h,
    },
  );
}
</script>

<template>
  <aside
    class="gallery"
    :class="{ detailing: !!selected }"
    aria-label="Add a widget"
  >
    <header>
      <h3>Add a widget</h3>
      <button type="button" class="x" aria-label="Close" @click="emit('close')">
        &#10005;
      </button>
    </header>
    <div class="cols">
      <nav class="list" aria-label="Widgets">
        <input v-model="query" type="search" placeholder="Search widgets" />
        <div v-for="g in grouped" :key="g.category" class="group">
          <h4>{{ g.category }}</h4>
          <button
            v-for="def in g.items"
            :key="def.type"
            type="button"
            class="item"
            :class="{ on: def.type === selectedType }"
            @click="pick(def)"
          >
            <span class="icon" aria-hidden="true">{{
              def.name.charAt(0)
            }}</span>
            <span class="words">
              <strong>{{ def.name }}</strong>
              <small>{{ def.description }}</small>
            </span>
          </button>
        </div>
        <p v-if="!grouped.length" class="none">No widgets match that search.</p>
      </nav>

      <section v-if="selected" class="detail">
        <button type="button" class="back" @click="selectedType = null">
          &#8249; All widgets
        </button>
        <div
          class="stage"
          :style="{ height: `${stage.h * stage.scale + 32}px` }"
        >
          <div
            class="scaled"
            :style="{
              width: `${stage.w}px`,
              height: `${stage.h}px`,
              left: `calc(50% - ${(stage.w * stage.scale) / 2}px)`,
              transform: `scale(${stage.scale})`,
            }"
            inert
          >
            <WidgetHost
              :key="selected.type"
              preview
              :def="selected"
              :settings="draft"
              :variant="variant"
              :w="size.w"
              :h="size.h"
            />
          </div>
        </div>
        <div class="head">
          <div>
            <h3>{{ selected.name }}</h3>
            <p>{{ selected.details }}</p>
          </div>
          <button type="button" class="add" @click="add">Add to page</button>
        </div>
        <div v-if="sizes.length > 1" class="sizes">
          <span class="label">Size</span>
          <button
            v-for="s in sizes"
            :key="s.id"
            type="button"
            class="chip"
            :class="{ on: sizeChoice === s.id }"
            @click="sizeChoice = s.id"
          >
            {{ s.label }}
          </button>
        </div>
        <SettingsFields
          :def="selected"
          :settings="draft"
          :variant="variant"
          @change="onChange"
        />
      </section>
      <section v-else class="detail blank">
        <strong>Pick a widget</strong>
        <span
          >See it with your own titles and set every option before you add
          it.</span
        >
      </section>
    </div>
  </aside>
</template>

<style scoped>
.gallery {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  color: var(--ui-text);
}
header {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--ui-border-soft);
}
h3 {
  margin: 0;
  font-size: 1.05rem;
}
.x {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--ui-dim);
  cursor: pointer;
}
.x:hover {
  background: var(--ui-surface-2);
  color: var(--ui-text);
}
.cols {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
}
.list {
  min-height: 0;
  overflow-y: auto;
  padding: 14px 12px 24px 16px;
  border-right: 1px solid var(--ui-border-soft);
  scrollbar-width: thin;
}
input[type="search"] {
  width: 100%;
  margin-bottom: 8px;
  padding: 9px 11px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  background: var(--ui-bg-2);
  color: var(--ui-text);
  font: inherit;
  font-size: 0.86rem;
  box-sizing: border-box;
}
input[type="search"]:focus {
  outline: none;
  border-color: var(--ui-accent);
}
.group h4 {
  margin: 14px 4px 6px;
  color: var(--ui-faint);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px;
  border: 1px solid transparent;
  border-radius: var(--ui-radius-row);
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.item:hover {
  background: var(--ui-surface);
}
.item.on {
  border-color: var(--ui-accent-line);
  background: var(--ui-accent-soft);
}
.icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: var(--ui-surface-3);
  color: var(--ui-accent);
  font-weight: 800;
}
.words {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.item strong {
  font-size: 0.86rem;
}
.item small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ui-faint);
  font-size: 0.72rem;
}
.detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  padding: 16px 20px 28px;
  overflow-y: auto;
  scrollbar-width: thin;
}
.detail.blank {
  justify-content: center;
  align-items: center;
  text-align: center;
  color: var(--ui-dim);
  font-size: 0.86rem;
}
.detail.blank strong {
  color: var(--ui-text);
  font-size: 1rem;
}
.back {
  display: none;
  align-self: flex-start;
  padding: 4px 0;
  border: 0;
  background: none;
  color: var(--ui-accent);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
.stage {
  position: relative;
  flex: none;
  overflow: hidden;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-card);
  background: var(--ui-bg);
}
.scaled {
  position: absolute;
  top: 16px;
  transform-origin: top left;
  pointer-events: none;
}
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}
.head p {
  margin: 4px 0 0;
  color: var(--ui-dim);
  font-size: 0.82rem;
  line-height: 1.45;
}
.add {
  flex: none;
  padding: 9px 18px;
  border: 0;
  border-radius: var(--ui-radius-control);
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font: inherit;
  font-size: 0.86rem;
  font-weight: 700;
  cursor: pointer;
}
.add:hover {
  filter: brightness(1.08);
}
.sizes {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.label {
  margin-right: 6px;
  color: var(--ui-dim);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.chip {
  padding: 6px 12px;
  border: 1px solid var(--ui-border);
  border-radius: 999px;
  background: transparent;
  color: var(--ui-dim);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}
.chip.on {
  border-color: var(--ui-accent);
  background: var(--ui-accent-soft);
  color: var(--ui-accent);
}
.none {
  margin: 8px 4px;
  color: var(--ui-faint);
  font-size: 0.85rem;
}
@media (max-width: 760px) {
  .cols {
    grid-template-columns: minmax(0, 1fr);
  }
  .list {
    border-right: 0;
  }
  .gallery.detailing .list {
    display: none;
  }
  .gallery:not(.detailing) .detail {
    display: none;
  }
  .back {
    display: inline-block;
  }
}
</style>
