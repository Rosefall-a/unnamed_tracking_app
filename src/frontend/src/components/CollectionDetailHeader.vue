<script setup lang="ts">
// The title row of a collection or list page: name (with a link to its parent
// when it is nested), count, a Smart tag, sort, reorder, add, edit and delete.
// The page decides what each button does; this is only how they are laid out.
type SortMode = "manual" | "title" | "status";

defineProps<{
  title: string;
  crumb?: { label: string; to: string } | null;
  countText: string;
  // smart collections and lists have no stored order, so no manual sort
  isSmart: boolean;
  sortMode: SortMode;
  reorderMode: boolean;
  canReorder: boolean;
  canAdd: boolean;
  addLabel: string;
  canEdit: boolean;
  canDelete: boolean;
  deleting?: boolean;
}>();

const emit = defineEmits<{
  "update:sortMode": [mode: SortMode];
  reorder: [];
  add: [];
  edit: [];
  delete: [];
}>();
</script>

<template>
  <div class="header-row">
    <h1>
      <router-link v-if="crumb" :to="crumb.to" class="parent-crumb"
        >{{ crumb.label }} ›</router-link
      >
      {{ title }}
    </h1>
    <span class="count-badge">{{ countText }}</span>
    <span v-if="isSmart" class="smart-pill" title="Fills itself from a filter"
      >Smart</span
    >
    <div class="header-spacer"></div>
    <select
      :value="sortMode"
      class="ui-field"
      :disabled="reorderMode"
      title="Sort"
      @change="
        emit(
          'update:sortMode',
          ($event.target as HTMLSelectElement).value as SortMode,
        )
      "
    >
      <option v-if="!isSmart" value="manual">Manual order</option>
      <option value="title">Title</option>
      <option value="status">Status</option>
    </select>
    <button
      v-if="canReorder"
      type="button"
      class="ui-btn ui-btn-secondary"
      :class="{ on: reorderMode }"
      @click="emit('reorder')"
    >
      {{ reorderMode ? "Done" : "Reorder" }}
    </button>
    <button
      v-if="canAdd"
      type="button"
      class="ui-btn ui-btn-primary"
      @click="emit('add')"
    >
      {{ addLabel }}
    </button>
    <button
      v-if="canEdit"
      type="button"
      class="ui-btn ui-btn-secondary"
      @click="emit('edit')"
    >
      Edit
    </button>
    <button
      v-if="canDelete"
      type="button"
      class="ui-btn ui-btn-danger"
      :disabled="deleting"
      @click="emit('delete')"
    >
      {{ deleting ? "Deleting…" : "Delete" }}
    </button>
  </div>
</template>

<style scoped>
.header-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
  margin-bottom: 8px;
}

.header-spacer {
  flex: 1;
}

.header-row h1 {
  margin: 0 4px 0 0;
  font-size: 1.7rem;
  font-weight: 800;
}

.count-badge {
  color: #9c9c9c;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.06);
  padding: 4px 12px;
  border-radius: 999px;
}

.smart-pill {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #d68a34;
  background: rgba(214, 138, 52, 0.14);
  padding: 4px 10px;
  border-radius: 999px;
}
.parent-crumb {
  color: #666;
  font-size: 1.1rem;
  font-weight: 600;
  text-decoration: none;
  margin-right: 4px;
}

.parent-crumb:hover {
  color: #d68a34;
}
</style>
