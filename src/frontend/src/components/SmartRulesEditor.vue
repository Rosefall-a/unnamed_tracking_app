<script setup lang="ts">
// The rules of a smart collection or a library tab: one row per rule, and
// whether a game needs to match every rule or any one. The rows are edited in
// place; the parent checks them with rowsToConditions when it saves.
import { computed } from "vue";
import { SMART_FIELD_LABELS, statusesOf } from "../state/smartCollections";
import type { SmartField, SmartMatch } from "../state/smartCollections";
import {
  NUMBER_FIELDS,
  STATUS_OPTIONS,
  TEXT_FIELDS,
} from "../utils/smartRuleFields";
import type { RuleRow } from "../utils/smartRuleFields";

const props = defineProps<{
  tagOptions?: string[];
  sourceOptions?: string[];
  collectionOptions?: string[];
  // datalist ids must be unique on the page
  idPrefix?: string;
  // fields the parent asks for in its own way (a library tab picks statuses
  // with its own buttons)
  hideFields?: SmartField[];
  // extra rules on top of something else, so having none is fine
  optional?: boolean;
}>();
const match = defineModel<SmartMatch>("match", { required: true });
const rows = defineModel<RuleRow[]>("rows", { required: true });

const prefix = props.idPrefix ?? "rules";

const fieldLabels = computed(() =>
  (Object.keys(SMART_FIELD_LABELS) as SmartField[])
    .filter((f) => !props.hideFields?.includes(f))
    .map((f) => ({ key: f, label: SMART_FIELD_LABELS[f] })),
);

function addRow() {
  rows.value = [...rows.value, { field: fieldLabels.value[0].key, value: "" }];
}
function removeRow(index: number) {
  rows.value = rows.value.filter((_, i) => i !== index);
}
// a value typed for one kind of rule means nothing for another
function changeField(row: RuleRow, field: SmartField) {
  row.field = field;
  row.value = "";
}
// a status rule can name several statuses; a game with any of them matches
function hasStatus(row: RuleRow, status: string): boolean {
  return statusesOf(String(row.value ?? "")).includes(status);
}
function toggleStatus(row: RuleRow, status: string) {
  const picked = statusesOf(String(row.value ?? ""));
  const next = picked.includes(status)
    ? picked.filter((s) => s !== status)
    : [...picked, status];
  // kept in the usual status order so the rule reads the same every time
  row.value = STATUS_OPTIONS.filter((s) => next.includes(s)).join(",");
}
function setMode(row: RuleRow, value: string) {
  row.not = value === "out";
}
// a collection rule naming one you do not have (renamed outside the app, or
// deleted) matches nothing, so say so rather than leave a tab quietly empty
function missingCollection(row: RuleRow): boolean {
  const name = String(row.value ?? "")
    .trim()
    .toLowerCase();
  if (row.field !== "collection" || !name || !props.collectionOptions)
    return false;
  return !props.collectionOptions.some((c) => c.trim().toLowerCase() === name);
}
function listFor(field: SmartField): string | undefined {
  if (field === "tag") return `${prefix}-tag-options`;
  if (field === "source") return `${prefix}-source-options`;
  if (field === "collection") return `${prefix}-collection-options`;
  return undefined;
}
</script>

<template>
  <div class="field">
    <span>{{ optional ? "More rules (optional)" : "Rules" }}</span>
    <small v-if="optional && !rows.length" class="none-yet">
      None. Add one to narrow the tab by tag, platform, playtime and more.
    </small>
    <label v-if="rows.length > 1" class="match">
      Games that match
      <select v-model="match" class="ui-field">
        <option value="all">every rule</option>
        <option value="any">any one rule</option>
      </select>
    </label>
    <div v-for="(row, i) in rows" :key="i" class="rule-row">
      <select
        :value="row.not ? 'out' : 'in'"
        class="ui-field rule-mode"
        :class="{ out: row.not }"
        :aria-label="`Rule ${i + 1}: keep or leave out`"
        @change="setMode(row, ($event.target as HTMLSelectElement).value)"
      >
        <option value="in">Include</option>
        <option value="out">Leave out</option>
      </select>
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
        <option v-for="f in fieldLabels" :key="f.key" :value="f.key">
          {{ f.label }}
        </option>
      </select>
      <input
        v-if="NUMBER_FIELDS[row.field]"
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
        :list="listFor(row.field)"
        class="ui-field rule-value"
        :placeholder="TEXT_FIELDS[row.field]"
        :aria-label="SMART_FIELD_LABELS[row.field]"
      />
      <span v-else-if="row.field !== 'status'" class="rule-value" />
      <button
        v-if="rows.length > 1 || optional"
        type="button"
        class="ui-btn ui-btn-secondary remove"
        :aria-label="`Remove rule ${i + 1}`"
        @click="removeRow(i)"
      >
        ✕
      </button>
      <small v-if="missingCollection(row)" class="rule-warning">
        No collection is called "{{ row.value }}", so this rule matches no
        games.
      </small>
      <div
        v-if="row.field === 'status'"
        class="status-chips"
        role="group"
        :aria-label="`Rule ${i + 1} statuses`"
      >
        <button
          v-for="s in STATUS_OPTIONS"
          :key="s"
          type="button"
          class="status-chip"
          :class="{ on: hasStatus(row, s), out: row.not }"
          :aria-pressed="hasStatus(row, s)"
          @click="toggleStatus(row, s)"
        >
          {{ s }}
        </button>
      </div>
    </div>
    <datalist :id="`${prefix}-tag-options`">
      <option v-for="t in tagOptions ?? []" :key="t" :value="t" />
    </datalist>
    <datalist :id="`${prefix}-source-options`">
      <option v-for="s in sourceOptions ?? []" :key="s" :value="s" />
    </datalist>
    <datalist :id="`${prefix}-collection-options`">
      <option v-for="c in collectionOptions ?? []" :key="c" :value="c" />
    </datalist>
    <button type="button" class="text-button add-rule" @click="addRow">
      {{ optional && !rows.length ? "+ Add a rule" : "+ Add another rule" }}
    </button>
  </div>
</template>

<style scoped>
/* the same look the rules had inside the collection form */
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--ui-text-soft);
  margin-bottom: 14px;
  flex: 1;
}
.none-yet {
  font-size: 12px;
  color: var(--ui-dim-2);
}
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
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.rule-mode {
  flex: 0 0 auto;
  width: auto;
}
.rule-mode.out {
  border-color: color-mix(in srgb, var(--ui-danger) 55%, transparent);
}
.rule-warning {
  flex: 1 0 100%;
  font-size: 12px;
  color: var(--ui-danger);
}
.status-chips {
  flex: 1 0 100%;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 4px;
}
.status-chip {
  padding: 4px 10px;
  border: 1px solid var(--ui-border);
  border-radius: 999px;
  background: transparent;
  color: var(--ui-text-soft);
  font: inherit;
  font-size: 12.5px;
  text-transform: capitalize;
  cursor: pointer;
}
.status-chip:hover {
  border-color: var(--ui-border-strong);
}
.status-chip.on {
  border-color: var(--ui-accent-line);
  background: color-mix(in srgb, var(--ui-accent) 14%, transparent);
  color: var(--ui-heading);
}
.status-chip.on.out {
  border-color: color-mix(in srgb, var(--ui-danger) 55%, transparent);
  background: color-mix(in srgb, var(--ui-danger) 12%, transparent);
  text-decoration: line-through;
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
  background: none;
  border: none;
  padding: 2px 0;
  color: var(--ui-accent);
  font: inherit;
  font-size: 0.82rem;
  cursor: pointer;
}
.add-rule:hover {
  text-decoration: underline;
}
</style>
