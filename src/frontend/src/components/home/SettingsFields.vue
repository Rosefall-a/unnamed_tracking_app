<script setup lang="ts">
// The settings form of a widget, drawn from the widget's field list. It is used
// both for a widget already on the page and in the gallery before you add one.
// Changes are applied as you make them.
import { computed } from "vue";
import { commonFields, effectiveSettings } from "../../home/registry";
import type {
  FieldOption,
  SettingField,
  WidgetDefinition,
} from "../../home/registry";

const props = defineProps<{
  def: WidgetDefinition;
  settings: Record<string, unknown>;
  variant: string | null;
}>();

const emit = defineEmits<{
  change: [settings: Record<string, unknown>, variant: string | null];
}>();

const values = computed(() => effectiveSettings(props.def, props.settings));
const look = computed(() => commonFields(props.def));
// fields that only apply to some settings (the collection to show, only when
// the shelf shows one) are left out until they do
const shown = computed(() =>
  [props.def.fields, look.value].map((group) =>
    group.filter((f) => !f.when || f.when(values.value)),
  ),
);
function optionsOf(f: SettingField): FieldOption[] {
  if (f.type !== "select" && f.type !== "multi") return [];
  return typeof f.options === "function" ? f.options() : f.options;
}

function set(key: string, value: unknown) {
  emit("change", { ...props.settings, [key]: value }, props.variant);
}
function current(field: SettingField): string[] {
  const value = values.value[field.key];
  return Array.isArray(value) ? (value as string[]) : [];
}
function toggleIn(field: SettingField, option: string) {
  const list = current(field);
  set(
    field.key,
    list.includes(option)
      ? list.filter((v) => v !== option)
      : [...list, option],
  );
}
function num(field: Extract<SettingField, { type: "number" }>, raw: string) {
  const n = Number(raw);
  if (!Number.isFinite(n)) return;
  set(field.key, Math.min(field.max, Math.max(field.min, Math.round(n))));
}
</script>

<template>
  <div class="fields">
    <div v-if="def.variants.length" class="field">
      <span class="label">Layout</span>
      <div class="chips">
        <button
          v-for="v in def.variants"
          :key="v.id"
          type="button"
          class="chip"
          :class="{ on: (variant ?? def.variants[0].id) === v.id }"
          @click="emit('change', settings, v.id)"
        >
          {{ v.label }}
        </button>
      </div>
    </div>

    <template v-for="(group, gi) in shown" :key="gi">
      <h4 v-if="gi === 1" class="group">Appearance</h4>
      <div v-for="f in group" :key="f.key" class="field">
        <label v-if="f.type !== 'multi'" class="label" :for="`wf-${f.key}`">
          {{ f.label }}
        </label>
        <span v-else class="label">{{ f.label }}</span>
        <select
          v-if="f.type === 'select'"
          :id="`wf-${f.key}`"
          :value="String(values[f.key])"
          @change="set(f.key, ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="o in optionsOf(f)" :key="o.value" :value="o.value">
            {{ o.label }}
          </option>
        </select>
        <input
          v-else-if="f.type === 'number'"
          :id="`wf-${f.key}`"
          type="number"
          :min="f.min"
          :max="f.max"
          :value="Number(values[f.key])"
          @change="num(f, ($event.target as HTMLInputElement).value)"
        />
        <input
          v-else-if="f.type === 'text'"
          :id="`wf-${f.key}`"
          type="text"
          :placeholder="f.placeholder"
          :value="String(values[f.key] ?? '')"
          @input="set(f.key, ($event.target as HTMLInputElement).value)"
        />
        <input
          v-else-if="f.type === 'date'"
          :id="`wf-${f.key}`"
          type="date"
          :value="String(values[f.key] ?? '')"
          @change="set(f.key, ($event.target as HTMLInputElement).value)"
        />
        <textarea
          v-else-if="f.type === 'textarea'"
          :id="`wf-${f.key}`"
          rows="5"
          :value="String(values[f.key] ?? '')"
          @input="set(f.key, ($event.target as HTMLTextAreaElement).value)"
        ></textarea>
        <label v-else-if="f.type === 'toggle'" class="switch">
          <input
            :id="`wf-${f.key}`"
            type="checkbox"
            :checked="!!values[f.key]"
            @change="set(f.key, ($event.target as HTMLInputElement).checked)"
          />
          <span>{{ values[f.key] ? "On" : "Off" }}</span>
        </label>
        <div v-else-if="f.type === 'multi'" class="chips">
          <button
            v-for="o in optionsOf(f)"
            :key="o.value"
            type="button"
            class="chip"
            :class="{ on: current(f).includes(o.value) }"
            :aria-pressed="current(f).includes(o.value)"
            @click="toggleIn(f, o.value)"
          >
            {{ o.label }}
          </button>
        </div>
        <small v-if="f.help">{{ f.help }}</small>
      </div>
    </template>
  </div>
</template>

<style scoped>
.fields {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.group {
  margin: 8px 0 -4px;
  padding-top: 16px;
  border-top: 1px solid var(--ui-border-soft);
  color: var(--ui-text);
  font-size: 0.9rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.label {
  color: var(--ui-dim);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
select,
input[type="number"],
input[type="text"],
input[type="date"],
textarea {
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
select:focus,
input:focus,
textarea:focus {
  outline: none;
  border-color: var(--ui-accent);
}
textarea {
  resize: vertical;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
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
.chip:hover {
  color: var(--ui-text);
  border-color: var(--ui-border-strong);
}
.chip.on {
  border-color: var(--ui-accent);
  background: var(--ui-accent-soft);
  color: var(--ui-accent);
}
.switch {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--ui-text);
  font-size: 0.88rem;
}
.switch input {
  width: 18px;
  height: 18px;
  accent-color: var(--ui-accent);
}
small {
  color: var(--ui-faint);
  font-size: 0.76rem;
}
</style>
