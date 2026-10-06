<script setup lang="ts">
// "Add games" / "Add titles": a searchable list of what is not in the
// collection or list yet, one click each. Done closes it.
import UiModal from "./UiModal.vue";
import { vLazyBg } from "../directives/lazyBackground";

defineProps<{
  heading: string;
  results: {
    key: string;
    title: string;
    thumbUrl: string | null | undefined;
    kind: string;
  }[];
  error: string | null;
  // hold back "nothing left" until the library has loaded
  loaded?: boolean;
}>();

const search = defineModel<string>("search", { required: true });

const emit = defineEmits<{
  add: [key: string];
  close: [];
}>();
</script>

<template>
  <UiModal :title="heading" @close="emit('close')">
    <div class="add-modal">
      <input
        v-model="search"
        type="text"
        class="ui-field"
        placeholder="Search your library…"
        autofocus
      />
      <p v-if="error" class="ui-error-box">{{ error }}</p>
      <div class="add-results">
        <button
          v-for="r in results"
          :key="r.key"
          type="button"
          class="add-row"
          @click="emit('add', r.key)"
        >
          <span class="add-thumb" v-lazy-bg="r.thumbUrl"></span>
          <span class="add-title">{{ r.title }}</span>
          <span class="add-kind">{{ r.kind }}</span>
          <span class="add-plus">+</span>
        </button>
        <p v-if="(loaded ?? true) && !results.length" class="ui-state">
          Nothing left to add{{ search ? " for that search" : "" }}.
        </p>
      </div>
    </div>
    <template #footer>
      <button
        type="button"
        class="ui-btn ui-btn-primary"
        @click="emit('close')"
      >
        Done
      </button>
    </template>
  </UiModal>
</template>

<style scoped>
/* add-games dialog */
.add-results {
  overflow-y: auto;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.add-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: none;
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 6px;
  color: var(--ui-text);
  text-align: left;
  font-family: inherit;
  cursor: pointer;
}

.add-row:hover {
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
}

.add-thumb {
  width: 30px;
  height: 44px;
  border-radius: 4px;
  background: var(--ui-surface-2) center / cover;
  flex-shrink: 0;
}

.add-title {
  flex: 1;
  min-width: 0;
  font-size: 0.86rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.add-kind {
  color: var(--ui-faint);
  font-size: 0.7rem;
  text-transform: uppercase;
}

.add-plus {
  color: var(--ui-accent-text);
  font-weight: var(--ui-weight-title);
  font-size: 1.1rem;
  width: 20px;
  text-align: center;
}

.add-modal {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.add-modal h3 {
  margin: 0;
}
</style>
