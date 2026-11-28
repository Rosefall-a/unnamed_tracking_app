<script setup lang="ts">
// Create or edit a collection, the Games counterpart of ListFormModal. A
// collection is either Manual (you add and order the games) or Smart (a saved
// rule that fills itself from the whole library). The kind is chosen at
// creation and can't be flipped afterwards: hand-picked games and a rule's
// live results are different things, and silently dropping one for the other
// would lose work.
import { ref, computed } from "vue";
import type { SmartDefinition, SmartMatch } from "../state/smartCollections";
import SmartRulesEditor from "./SmartRulesEditor.vue";
import { rowsToConditions } from "../utils/smartRuleFields";
import type { RuleRow } from "../utils/smartRuleFields";

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
const rows = ref<RuleRow[]>(
  props.collection?.smart?.rules.map((r) => ({ ...r })) ?? [
    { field: "status", value: "" },
  ],
);
const match = ref<SmartMatch>(props.collection?.smart?.match ?? "all");
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
  let definition: SmartDefinition | null = null;
  if (smart.value) {
    const found = rowsToConditions(rows.value);
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

      <SmartRulesEditor
        v-if="smart"
        v-model:match="match"
        v-model:rows="rows"
        :tag-options="tagOptions"
        :source-options="sourceOptions"
        :collection-options="existingNames"
        id-prefix="collection"
      />

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
