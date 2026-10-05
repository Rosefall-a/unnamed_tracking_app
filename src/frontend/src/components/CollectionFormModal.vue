<script setup lang="ts">
// Create or edit a collection, the Games counterpart of ListFormModal. A
// collection is either Manual (you add and order the games) or Smart (a saved
// rule that fills itself from the whole library). The kind is chosen at
// creation and can't be flipped afterwards: hand-picked games and a rule's
// live results are different things, and silently dropping one for the other
// would lose work.
import { ref, computed } from "vue";
import UiModal from "./UiModal.vue";
import { SMART_FIELD_LABELS } from "../state/smartCollections";
import type { SmartField } from "../state/smartCollections";
import type { GameStatus } from "../types/game";

export interface CollectionFormPayload {
  name: string;
  description: string | null;
  smart: { field: SmartField; value: string } | null;
}

const props = defineProps<{
  // set = editing that collection; null = creating
  collection: {
    name: string;
    description: string | null;
    smart: { field: SmartField; value: string } | null;
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

const editing = computed(() => props.collection !== null);
const name = ref(props.collection?.name ?? "");
const description = ref(props.collection?.description ?? "");
const smart = ref(props.collection?.smart != null);
const field = ref<SmartField>(props.collection?.smart?.field ?? "status");
const value = ref(props.collection?.smart?.value ?? "");
const error = ref<string | null>(null);

function taken(candidate: string): boolean {
  return props.existingNames.some(
    (n) =>
      n.toLowerCase() === candidate.toLowerCase() &&
      n !== props.collection?.name,
  );
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
  if (smart.value && field.value !== "favorite" && !value.value.trim()) {
    error.value = "Pick a value for the rule.";
    return;
  }
  emit("save", {
    name: trimmed,
    description: description.value.trim() || null,
    smart: smart.value
      ? {
          field: field.value,
          value: field.value === "favorite" ? "" : value.value.trim(),
        }
      : null,
  });
}
</script>

<template>
  <UiModal
    :title="editing ? 'Edit collection' : 'Create a collection'"
    @close="emit('close')"
  >
    <form @submit.prevent="submit">
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
        <label class="field">
          <span>Rule</span>
          <select v-model="field" class="ui-field">
            <option
              v-for="(label, key) in SMART_FIELD_LABELS"
              :key="key"
              :value="key"
            >
              {{ label }}
            </option>
          </select>
        </label>
        <label v-if="field === 'status'" class="field">
          <span>Value</span>
          <select v-model="value" class="ui-field">
            <option value="">Select…</option>
            <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">
              {{ s }}
            </option>
          </select>
        </label>
        <label v-else-if="field === 'playtime_hours'" class="field">
          <span>Hours</span>
          <input
            v-model="value"
            type="number"
            min="0"
            class="ui-field"
            placeholder="e.g. 20"
          />
        </label>
        <label v-else-if="field === 'tag'" class="field">
          <span>Tag</span>
          <input
            v-model="value"
            type="text"
            list="collection-tag-options"
            class="ui-field"
            placeholder="e.g. RPG"
          />
          <datalist id="collection-tag-options">
            <option v-for="t in tagOptions" :key="t" :value="t" />
          </datalist>
        </label>
        <label v-else-if="field === 'source'" class="field">
          <span>Source</span>
          <input
            v-model="value"
            type="text"
            list="collection-source-options"
            class="ui-field"
            placeholder="e.g. Steam"
          />
          <datalist id="collection-source-options">
            <option v-for="s in sourceOptions" :key="s" :value="s" />
          </datalist>
        </label>
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
  </UiModal>
</template>

<style scoped>
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
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-row);
  padding: 10px 12px;
  color: var(--ui-text);
  font-family: inherit;
  cursor: pointer;
}
.kind-pick button strong {
  font-size: 0.86rem;
  color: var(--ui-text);
}
.kind-pick button span {
  font-size: 0.72rem;
  color: var(--ui-dim);
}
.kind-pick button.active {
  border-color: var(--ui-accent-line);
  background: color-mix(in srgb, var(--ui-accent) 10%, transparent);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--ui-text);
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
