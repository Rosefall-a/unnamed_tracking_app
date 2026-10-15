<script setup lang="ts">
// A note to yourself. Click it and type: it is saved as you go, so it needs no
// settings or edit mode. (In a preview, or while you are rearranging the page, it
// just shows the text.)
import { computed, inject, ref, watch } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { WIDGET_CONTEXT } from "../../../home/context";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();
const ctx = inject(WIDGET_CONTEXT, null);

const saved = computed(() =>
  props.sample
    ? "Finish the campaign before the sale ends."
    : String(props.settings.text ?? ""),
);
const draft = ref(saved.value);
watch(saved, (v) => {
  if (v !== draft.value) draft.value = v;
});

let timer: number | undefined;
function onInput() {
  window.clearTimeout(timer);
  timer = window.setTimeout(
    () => ctx?.value?.update({ text: draft.value }),
    500,
  );
}
function flush() {
  window.clearTimeout(timer);
  if (draft.value !== saved.value) ctx?.value?.update({ text: draft.value });
}
const editable = computed(() => !props.sample && !!ctx?.value);
</script>

<template>
  <WidgetFrame title="Note" surface :sample="sample">
    <textarea
      v-if="editable"
      v-model="draft"
      class="note"
      placeholder="Write a note..."
      spellcheck="true"
      @input="onInput"
      @blur="flush"
    ></textarea>
    <p v-else class="text">{{ saved || "Nothing written yet." }}</p>
  </WidgetFrame>
</template>

<style scoped>
.note,
.text {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ui-text);
  font: inherit;
  font-size: 0.92rem;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  box-sizing: border-box;
}
.note {
  resize: none;
}
.note:focus {
  outline: none;
}
.note::placeholder {
  color: var(--ui-faint);
}
</style>
