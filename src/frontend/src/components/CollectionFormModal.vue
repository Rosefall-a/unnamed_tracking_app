<script setup lang="ts">
// Create or edit a collection, the Games counterpart of ListFormModal. A
// collection is either Manual (you add and order the games) or Smart (a saved
// rule that fills itself from the whole library). The kind is chosen at
// creation and can't be flipped afterwards: hand-picked games and a rule's
// live results are different things, and silently dropping one for the other
// would lose work.
import { ref, computed } from "vue";
import { SMART_FIELD_LABELS } from "../state/smartCollections";
import type {
  SmartCondition,
  SmartDefinition,
  SmartField,
  SmartMatch,
} from "../state/smartCollections";
import type { GameStatus } from "../types/game";

export interface CollectionFormPayload {
  name: string;
  description: string | null;
  smart: SmartDefinition | null;
}

const props = defineProps<{
  // set = editing that collection; null = creating
  collection: {
    name: string;
    description: string | null;
    smart: SmartDefinition | null;
  } | null;
  existingNames: string[];
  tagOptions: string[];
  sourceOptions: string[];
}>();

const emit = defineEmits<{
  save: [payload: CollectionFormPayload];
  close: [];
}>();

const STATUS_OPTIONS: GameStatus[] = [
  "playing",
  "beaten",
  "mastered",
  "played",
  "on hold",
  "dropped",
  "backlog",
  "wishlist",
];
// one-click starters, a blank name gives no sense of what a collection is for
const STARTER_TEMPLATES = [
  "Currently Playing",
  "Backlog Priority",
  "Co-op Games",
];

// what kind of box each rule's value needs, and the hint shown in it
const TEXT_FIELDS: Partial<Record<SmartField, string>> = {
  tag: "e.g. RPG",
  source: "e.g. Steam",
  platform: "e.g. PC",
  series: "e.g. Dark Souls",
};
const NUMBER_FIELDS: Partial<
  Record<SmartField, { min: number; max: number; hint: string }>
> = {
  playtime_hours: { min: 0, max: 100000, hint: "hours, e.g. 20" },
  achievement_percent: { min: 0, max: 100, hint: "%, e.g. 80" },
  priority: { min: 1, max: 5, hint: "1 to 5" },
  finished_year: { min: 1950, max: 2100, hint: "e.g. 2026" },
  released_from: { min: 1950, max: 2100, hint: "e.g. 2010" },
  released_to: { min: 1950, max: 2100, hint: "e.g. 2015" },
  added_within_days: { min: 1, max: 36500, hint: "days, e.g. 30" },
  played_within_days: { min: 1, max: 36500, hint: "days, e.g. 30" },
  not_played_days: { min: 1, max: 36500, hint: "days, e.g. 180" },
};

interface Row {
  field: SmartField;
  // a number box hands back a number, so either is read as text on save
  value: string | number;
}

const editing = computed(() => props.collection !== null);
const name = ref(props.collection?.name ?? "");
const description = ref(props.collection?.description ?? "");
const smart = ref(props.collection?.smart != null);
const rows = ref<Row[]>(
  props.collection?.smart?.rules.map((r) => ({ ...r })) ?? [
    { field: "status", value: "" },
  ],
);
const match = ref<SmartMatch>(props.collection?.smart?.match ?? "all");
const error = ref<string | null>(null);

function addRow() {
  rows.value.push({ field: "status", value: "" });
}
function removeRow(index: number) {
  rows.value.splice(index, 1);
}
// a value typed for one kind of rule means nothing for another
function changeField(row: Row, field: SmartField) {
  row.field = field;
  row.value = "";
}

function taken(candidate: string): boolean {
  return props.existingNames.some(
    (n) =>
      n.toLowerCase() === candidate.toLowerCase() &&
      n !== props.collection?.name,
  );
}

function conditions(): SmartCondition[] | string {
  const out: SmartCondition[] = [];
  for (const row of rows.value) {
    const value = String(row.value ?? "").trim();
    const label = SMART_FIELD_LABELS[row.field];
    if (row.field === "favorite") {
      out.push({ field: "favorite", value: "" });
      continue;
    }
    if (!value) return `Fill in "${label}".`;
    const limits = NUMBER_FIELDS[row.field];
    if (limits) {
      const n = Number(value);
      if (!Number.isFinite(n) || n < limits.min || n > limits.max)
        return `"${label}" needs a number from ${limits.min} to ${limits.max}.`;
    }
    out.push({ field: row.field, value });
  }
  return out.length ? out : "Add at least one rule.";
}

function submit() {
  const trimmed = name.value.trim();
  if (!trimmed) {
    error.value = "Give the collection a name.";
    return;
  }
  if (taken(trimmed)) {
    error.value = `"${trimmed}" already exists.`;
    return;
  }
  let definition: SmartDefinition | null = null;
  if (smart.value) {
    const found = conditions();
    if (typeof found === "string") {
      error.value = found;
      return;
    }
    definition = { ...found[0], rules: found, match: match.value };
  }
  emit("save", {
    name: trimmed,
    description: description.value.trim() || null,
    smart: definition,
  });
}
</script>

<template>
  <div class="ui-backdrop" @click.self="emit('close')">
    <form
      class="ui-modal"
      role="dialog"
      aria-modal="true"
      @submit.prevent="submit"
    >
      <h3>{{ editing ? "Edit collection" : "Create a collection" }}</h3>

      <div v-if="!editing" class="kind-pick">
        <button
          type="button"
          :class="{ active: !smart }"
          @click="smart = false"
        >
          <strong>Manual</strong>
          <span>You add and order the games</span>
        </button>
        <button type="button" :class="{ active: smart }" @click="smart = true">
          <strong>Smart</strong>
          <span>Fills itself from a rule</span>
        </button>
      </div>

      <label class="field">
        <span>Name</span>
        <input
          v-model="name"
          type="text"
          class="ui-field"
          maxlength="200"
          autofocus
        />
        <small>Use "Parent/Child" to nest it under another.</small>
      </label>
      <div v-if="!editing && !smart" class="chips">
        <button
          v-for="t in STARTER_TEMPLATES"
          :key="t"
          type="button"
          class="ui-chip"
          :disabled="taken(t)"
          @click="name = t"
        >
          {{ t }}
        </button>
      </div>
      <label class="field">
        <span>Description (optional)</span>
        <input v-model="description" type="text" class="ui-field" />
      </label>

      <template v-if="smart">
        <div class="field">
          <span>Rules</span>
          <label v-if="rows.length > 1" class="match">
            Games that match
            <select v-model="match" class="ui-field">
              <option value="all">every rule</option>
              <option value="any">any one rule</option>
            </select>
          </label>
          <div v-for="(row, i) in rows" :key="i" class="rule-row">
            <select
              :value="row.field"
              class="ui-field rule-field"
              :aria-label="`Rule ${i + 1}`"
              @change="
                changeField(
                  row,
                  ($event.target as HTMLSelectElement).value as SmartField,
                )
              "
            >
              <option
                v-for="(label, key) in SMART_FIELD_LABELS"
                :key="key"
                :value="key"
              >
                {{ label }}
              </option>
            </select>
            <select
              v-if="row.field === 'status'"
              v-model="row.value"
              class="ui-field rule-value"
              aria-label="Status"
            >
              <option value="">Select…</option>
              <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">
                {{ s }}
              </option>
            </select>
            <input
              v-else-if="NUMBER_FIELDS[row.field]"
              v-model="row.value"
              type="number"
              :min="NUMBER_FIELDS[row.field]!.min"
              :max="NUMBER_FIELDS[row.field]!.max"
              class="ui-field rule-value"
              :placeholder="NUMBER_FIELDS[row.field]!.hint"
              :aria-label="SMART_FIELD_LABELS[row.field]"
            />
            <input
              v-else-if="TEXT_FIELDS[row.field] !== undefined"
              v-model="row.value"
              type="text"
              :list="
                row.field === 'tag'
                  ? 'collection-tag-options'
                  : row.field === 'source'
                    ? 'collection-source-options'
                    : undefined
              "
              class="ui-field rule-value"
              :placeholder="TEXT_FIELDS[row.field]"
              :aria-label="SMART_FIELD_LABELS[row.field]"
            />
            <span v-else class="rule-value" />
            <button
              v-if="rows.length > 1"
              type="button"
              class="ui-btn ui-btn-secondary remove"
              :aria-label="`Remove rule ${i + 1}`"
              @click="removeRow(i)"
            >
              ✕
            </button>
          </div>
          <datalist id="collection-tag-options">
            <option v-for="t in tagOptions" :key="t" :value="t" />
          </datalist>
          <datalist id="collection-source-options">
            <option v-for="s in sourceOptions" :key="s" :value="s" />
          </datalist>
          <button type="button" class="text-button add-rule" @click="addRow">
            + Add another rule
          </button>
        </div>
      </template>

      <p v-if="error" class="ui-error-box">{{ error }}</p>

      <div class="ui-modal-actions">
        <button
          type="button"
          class="ui-btn ui-btn-secondary"
          @click="emit('close')"
        >
          Cancel
        </button>
        <button type="submit" class="ui-btn ui-btn-primary">
          {{ editing ? "Save" : "Create" }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.match {
  display: flex;
  align-items: center;
  gap: 8px;
}
.match .ui-field {
  width: auto;
}
.rule-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.rule-field {
  flex: 1 1 55%;
  min-width: 0;
}
.rule-value {
  flex: 1 1 45%;
  min-width: 0;
}
.remove {
  flex: 0 0 auto;
  padding: 6px 10px;
}
.add-rule {
  align-self: flex-start;
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
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--ui-text-soft);
  margin-bottom: 14px;
  flex: 1;
}
.field small {
  color: var(--ui-faint);
  font-size: 0.72rem;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: -6px 0 14px;
}
.chips .ui-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
