<script setup lang="ts">
// The settings of one widget on the page, with its size, and a way to remove it.
import { ref } from "vue";
import SettingsFields from "./SettingsFields.vue";
import { GRID_COLUMNS } from "../../home/layout";
import type { WidgetDefinition } from "../../home/registry";

const props = defineProps<{
  def: WidgetDefinition;
  settings: Record<string, unknown>;
  variant: string | null;
  w: number;
  h: number;
}>();

const emit = defineEmits<{
  change: [settings: Record<string, unknown>, variant: string | null];
  resize: [w: number, h: number];
  remove: [];
  close: [];
}>();

// the smallest a widget can be is part of what it is; say so when it is asked for less
const note = ref<string | null>(null);
function size(kind: "w" | "h", raw: string, input: HTMLInputElement) {
  const n = Math.round(Number(raw));
  if (!Number.isFinite(n)) return;
  const { minW, minH } = props.def.size;
  note.value = null;
  if (kind === "w") {
    const w = Math.min(GRID_COLUMNS, Math.max(minW, n));
    if (n < minW)
      note.value = `${props.def.name} needs at least ${minW} columns.`;
    if (n > GRID_COLUMNS)
      note.value = `The page is ${GRID_COLUMNS} columns wide.`;
    input.value = String(w);
    emit("resize", w, props.h);
  } else {
    const h = Math.min(40, Math.max(minH, n));
    if (n < minH) note.value = `${props.def.name} needs at least ${minH} rows.`;
    input.value = String(h);
    emit("resize", props.w, h);
  }
}
</script>

<template>
  <aside class="panel" aria-label="Widget settings">
    <header>
      <div>
        <h3>{{ def.name }}</h3>
        <p>{{ def.description }}</p>
      </div>
      <button type="button" class="x" aria-label="Close" @click="emit('close')">
        &#10005;
      </button>
    </header>
    <div class="body">
      <div class="size">
        <label>
          <span class="label">Width (columns)</span>
          <input
            type="number"
            :min="def.size.minW"
            :max="GRID_COLUMNS"
            :value="w"
            @change="
              size(
                'w',
                ($event.target as HTMLInputElement).value,
                $event.target as HTMLInputElement,
              )
            "
          />
        </label>
        <label>
          <span class="label">Height (rows)</span>
          <input
            type="number"
            :min="def.size.minH"
            max="40"
            :value="h"
            @change="
              size(
                'h',
                ($event.target as HTMLInputElement).value,
                $event.target as HTMLInputElement,
              )
            "
          />
        </label>
      </div>
      <p class="hint" :class="{ warn: note }">
        {{
          note ??
          `Smallest size: ${def.size.minW} columns wide, ${def.size.minH} rows tall.`
        }}
      </p>
      <SettingsFields
        :def="def"
        :settings="settings"
        :variant="variant"
        @change="(s, v) => emit('change', s, v)"
      />
      <button type="button" class="remove" @click="emit('remove')">
        Remove this widget
      </button>
    </div>
  </aside>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  color: var(--ui-text);
}
header {
  flex: none;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--ui-border-soft);
}
h3 {
  margin: 0;
  font-size: 1.05rem;
}
header p {
  margin: 4px 0 0;
  color: var(--ui-faint);
  font-size: 0.8rem;
}
.x {
  flex: none;
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
.body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 18px 20px 24px;
}
.size {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.size label {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.hint {
  margin: -8px 0 0;
  color: var(--ui-faint);
  font-size: 0.76rem;
}
.hint.warn {
  color: var(--ui-accent);
}
.label {
  color: var(--ui-dim);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
input[type="number"] {
  width: 100%;
  padding: 9px 11px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  background: var(--ui-bg-2);
  color: var(--ui-text);
  font: inherit;
  font-size: 0.88rem;
  box-sizing: border-box;
}
input:focus {
  outline: none;
  border-color: var(--ui-accent);
}
.remove {
  align-self: flex-start;
  padding: 8px 14px;
  border: 1px solid color-mix(in srgb, var(--ui-danger) 60%, transparent);
  border-radius: var(--ui-radius-control);
  background: transparent;
  color: var(--ui-error-text);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
}
.remove:hover {
  background: color-mix(in srgb, var(--ui-danger) 14%, transparent);
}
</style>
