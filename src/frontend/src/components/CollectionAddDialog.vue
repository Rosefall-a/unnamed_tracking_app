<script setup lang="ts">
// "Add games" / "Add titles": a searchable list of what is not in the
// collection or list yet, one click each. Done closes it.
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
  <div class="ui-backdrop" @click.self="emit('close')">
    <div class="ui-modal add-modal">
      <h3>{{ heading }}</h3>
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
      <div class="ui-modal-actions">
        <button
          type="button"
          class="ui-btn ui-btn-primary"
          @click="emit('close')"
        >
          Done
        </button>
      </div>
    </div>
  </div>
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
  border-radius: 8px;
  padding: 6px;
  color: #ddd;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
}

.add-row:hover {
  background: rgba(255, 255, 255, 0.06);
}

.add-thumb {
  width: 30px;
  height: 44px;
  border-radius: 4px;
  background: #262626 center / cover;
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
  color: #666;
  font-size: 0.7rem;
  text-transform: uppercase;
}

.add-plus {
  color: #d68a34;
  font-weight: 800;
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
