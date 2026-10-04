<script setup lang="ts">
import { computed, ref } from "vue";
import UiModal from "./UiModal.vue";
import type { HomeWidgetChoice } from "../services/homeWidgets";
import { selectedHomeWidgets } from "../services/homeWidgets";

const props = defineProps<{
  choices: HomeWidgetChoice[];
  selected: string[];
  busy: boolean;
  error: string | null;
  loading: boolean;
}>();
const emit = defineEmits<{ close: []; save: [ids: string[]] }>();
const draft = ref([...props.selected]);
const ordered = computed(() => selectedHomeWidgets(draft.value, props.choices));
function toggle(id: string) {
  draft.value = draft.value.includes(id)
    ? draft.value.filter((item) => item !== id)
    : [...draft.value, id];
}
function move(index: number, direction: -1 | 1) {
  const next = [...draft.value];
  const target = index + direction;
  if (target < 0 || target >= next.length) return;
  [next[index], next[target]] = [next[target]!, next[index]!];
  draft.value = next;
}
</script>

<template>
  <UiModal
    title="Customize Home"
    description="Choose what appears on your Home page. Your selection and order follow your account."
    :dismissible="!busy"
    @close="emit('close')"
  >
    <p v-if="error" role="alert" class="ui-alert">{{ error }}</p>
    <fieldset :disabled="busy" class="widget-fields">
      <h3>Choose widgets</h3>
      <p v-if="loading" role="status" class="hint">Loading your collections…</p>
      <label v-for="choice in choices" :key="choice.id" class="widget-choice">
        <input
          type="checkbox"
          :checked="draft.includes(choice.id)"
          :disabled="!draft.includes(choice.id) && draft.length >= 32"
          @change="toggle(choice.id)"
        />
        <span
          ><strong>{{ choice.title }}</strong
          ><small>{{ choice.description }}</small></span
        >
      </label>
      <h3>Widget order</h3>
      <p v-if="!ordered.length" class="hint">
        Keep Home minimal, or choose a widget above.
      </p>
      <ol v-else class="widget-order">
        <li v-for="(widget, index) in ordered" :key="widget.id">
          <span
            >{{ widget.title
            }}<small v-if="widget.available === false">Unavailable</small></span
          >
          <div class="order-actions">
            <button
              type="button"
              class="ui-btn ui-btn-ghost"
              :disabled="index === 0"
              :aria-label="`Move ${widget.title} up`"
              @click="move(index, -1)"
            >
              ↑
            </button>
            <button
              type="button"
              class="ui-btn ui-btn-ghost"
              :disabled="index === ordered.length - 1"
              :aria-label="`Move ${widget.title} down`"
              @click="move(index, 1)"
            >
              ↓
            </button>
            <button
              type="button"
              class="ui-btn ui-btn-ghost"
              :aria-label="`Remove ${widget.title}`"
              @click="toggle(widget.id)"
            >
              Remove
            </button>
          </div>
        </li>
      </ol>
    </fieldset>
    <template #footer>
      <button
        type="button"
        class="ui-btn ui-btn-ghost"
        :disabled="busy"
        @click="emit('close')"
      >
        Cancel
      </button>
      <button
        type="button"
        class="ui-btn ui-btn-primary"
        :disabled="busy"
        @click="emit('save', draft)"
      >
        {{ busy ? "Saving…" : "Save Home" }}
      </button>
    </template>
  </UiModal>
</template>

<style scoped>
.widget-fields {
  border: 0;
  padding: 0;
  margin: 0;
  min-width: 0;
}
h3 {
  font: var(--ui-weight-heading) var(--ui-font-body)/1.5 var(--ui-font-family);
  margin: 0 0 12px;
}
h3:not(:first-child) {
  margin-top: 24px;
}
.hint,
small {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
}
.widget-choice {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 4px;
  border-bottom: 1px solid var(--ui-border-soft);
  cursor: pointer;
}
.widget-choice input {
  flex-shrink: 0;
  appearance: none;
  width: 20px;
  height: 20px;
  border: 1.5px solid var(--ui-border-strong);
  border-radius: 5px;
  background: var(--ui-surface);
  display: grid;
  place-content: center;
  margin: 0;
}
.widget-choice input:checked {
  background: var(--ui-accent);
  border-color: var(--ui-accent);
}
.widget-choice input:checked::before {
  content: "";
  width: 5px;
  height: 10px;
  border-right: 2px solid var(--ui-on-accent);
  border-bottom: 2px solid var(--ui-on-accent);
  transform: translateY(-1px) rotate(45deg);
}
.widget-choice span {
  min-width: 0;
}
.widget-choice strong {
  font-weight: 600;
}
small {
  display: block;
  margin-top: 4px;
  overflow-wrap: anywhere;
}
.widget-order {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.widget-order li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: var(--ui-surface-2);
  padding: 12px;
  border-radius: var(--ui-radius-row);
}
.widget-order li > span {
  overflow-wrap: anywhere;
  min-width: 0;
}
.order-actions {
  display: flex;
  gap: 6px;
}
.order-actions button {
  min-height: var(--ui-control-height);
  min-width: var(--ui-control-height);
}
</style>
