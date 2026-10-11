<script setup lang="ts" generic="S extends string, K extends string">
// The top of a Collections overview page, the same for Games and for Media: the
// title, a search box, the sort, "+ Create Collection", and the filter tabs under
// them. A page can add more filters in the `filters` slot.
import SegmentedTabs from "./SegmentedTabs.vue";
import type { SegmentOption } from "./SegmentedTabs.vue";

defineProps<{
  title: string;
  // what the search box looks for, as it reads in "Search ...": "collections"
  searchLabel: string;
  sortOptions: { value: S; label: string }[];
  kindOptions: SegmentOption[];
}>();
const search = defineModel<string>("search", { required: true });
const sort = defineModel<S>("sort", { required: true });
const kind = defineModel<K>("kind", { required: true });
const emit = defineEmits<{ create: [] }>();
</script>

<template>
  <div class="ui-head">
    <h1>{{ title }}</h1>
    <div class="header-actions">
      <input
        v-model="search"
        type="text"
        class="ui-field search-input"
        :placeholder="`Search ${searchLabel}…`"
        :aria-label="`Search ${searchLabel}`"
      />
      <select v-model="sort" class="ui-field sort-select" aria-label="Sort by">
        <option v-for="o in sortOptions" :key="o.value" :value="o.value">
          {{ o.label }}
        </option>
      </select>
      <button
        type="button"
        class="ui-btn ui-btn-primary"
        @click="emit('create')"
      >
        + Create Collection
      </button>
    </div>
  </div>

  <div class="filter-row">
    <SegmentedTabs
      :options="kindOptions"
      :model-value="kind"
      aria-label="Filter by kind of collection"
      @update:model-value="kind = $event as K"
    />
    <slot name="filters" />
  </div>
</template>

<style scoped>
.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.search-input {
  width: 220px;
}

/* a select sizes itself to its longest option, so without this the sort box was
   wider on the pages with longer option names */
.sort-select {
  width: 172px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin-bottom: 20px;
}
</style>
