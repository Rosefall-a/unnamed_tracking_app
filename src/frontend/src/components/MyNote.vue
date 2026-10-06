<script setup lang="ts">
// Your own note on a title, shown on its page. It is private to you: notes
// will stay that way when titles become shared between people.
import { ref, watch, nextTick } from "vue";

const props = defineProps<{ note: string | null }>();
const emit = defineEmits<{ (e: "save", note: string | null): void }>();

const editing = ref(false);
const draft = ref(props.note ?? "");
const input = ref<HTMLTextAreaElement | null>(null);

watch(
  () => props.note,
  (value) => {
    if (!editing.value) draft.value = value ?? "";
  },
);

// grows with what is typed, so a long note never hides behind a scrollbar
function fit() {
  const el = input.value;
  if (!el) return;
  el.style.height = "auto";
  // scrollHeight leaves out the 1px top and bottom border
  el.style.height = `${el.scrollHeight + 2}px`;
}
async function startEdit() {
  draft.value = props.note ?? "";
  editing.value = true;
  await nextTick();
  fit();
  input.value?.focus();
}
function cancel() {
  editing.value = false;
}
function save() {
  emit("save", draft.value.trim() || null);
  editing.value = false;
}
</script>

<template>
  <section class="my-note" :class="{ empty: !note && !editing }">
    <template v-if="editing">
      <header class="note-head">
        <h3>Your note</h3>
        <span class="note-private">Only you can see this</span>
      </header>
      <textarea
        ref="input"
        v-model="draft"
        class="note-input"
        rows="3"
        placeholder="Anything you want to remember about this title"
        aria-label="Your note"
        @input="fit"
        @keydown.esc="cancel"
        @keydown.ctrl.enter="save"
        @keydown.meta.enter="save"
      ></textarea>
      <div class="note-actions">
        <button type="button" class="btn-solid" @click="save">Save</button>
        <button type="button" class="btn-text muted" @click="cancel">
          Cancel
        </button>
        <span class="note-hint">Ctrl+Enter to save</span>
      </div>
    </template>

    <template v-else-if="note">
      <header class="note-head">
        <h3>Your note</h3>
        <span class="note-private">Only you can see this</span>
        <button type="button" class="btn-text" @click="startEdit">Edit</button>
      </header>
      <p class="note-text">{{ note }}</p>
    </template>

    <template v-else>
      <button type="button" class="btn-text" @click="startEdit">
        + Add a note
      </button>
      <span class="note-private">Only you can see this</span>
    </template>
  </section>
</template>

<style scoped>
/* Matches the rest of the title page: the "Seasons" heading, the description's
   type, the amber text links and the dark inputs, with a hairline instead of a box. */
.my-note {
  margin-top: 26px;
  padding-top: 22px;
  border-top: 1px solid #1f1f1f;
}
.my-note.empty {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.note-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0 0 10px;
}
.note-head h3 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: var(--ui-weight-title);
  color: var(--ui-text);
}
.note-private {
  flex: 1;
  font-size: 0.72rem;
  color: var(--ui-faint);
}
.note-text {
  margin: 0;
  font-size: 0.96rem;
  line-height: 1.7;
  color: #d0d0d0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.note-input {
  display: block;
  width: 100%;
  box-sizing: border-box;
  min-height: 84px;
  resize: none;
  overflow: hidden;
  padding: 12px 14px;
  border-radius: var(--ui-radius-row);
  border: 1px solid var(--ui-border);
  background: var(--ui-surface);
  color: var(--ui-text);
  font: inherit;
  font-size: 0.96rem;
  line-height: 1.7;
}
.note-input::placeholder {
  color: var(--ui-faint);
}
.note-input:focus {
  outline: none;
  border-color: color-mix(in srgb, var(--ui-accent) 70%, transparent);
}
.note-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 12px;
}
.note-hint {
  margin-left: auto;
  font-size: 0.72rem;
  color: var(--ui-faint);
}
.btn-text {
  background: none;
  border: none;
  /* larger tap target without moving the text */
  padding: 6px 4px;
  margin: -6px -4px;
  color: var(--ui-accent-text);
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-text:hover {
  color: var(--ui-accent);
}
.btn-text.muted {
  color: var(--ui-dim);
}
.btn-text.muted:hover {
  color: var(--ui-text);
}
.btn-solid {
  background: var(--ui-accent);
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 8px 18px;
  color: var(--ui-on-accent);
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: var(--ui-weight-title);
  cursor: pointer;
}
.btn-solid:hover {
  background: #e29a48;
}
.btn-text:focus-visible,
.btn-solid:focus-visible {
  outline: 2px solid var(--ui-accent-text);
  outline-offset: 3px;
  border-radius: 4px;
}
</style>
