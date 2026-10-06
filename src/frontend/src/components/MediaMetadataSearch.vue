<script setup lang="ts">
// The "Search TMDB / OMDb" box at the top of the Movie, TV and Anime forms:
// a query, the matches, and the messages around them. Picking a match tells
// the form, which fills in its own fields.
defineProps<{
  label: string;
  // "movie", "show" or "anime", for the placeholder
  noun: string;
  results: { key: string; title: string; provider: string; detail?: string }[];
  searching: boolean;
  message: string | null;
  warnings: string[];
}>();

const query = defineModel<string>("query", { required: true });

const emit = defineEmits<{
  search: [];
  pick: [key: string];
}>();
</script>

<template>
  <div class="field">
    <span>{{ label }}</span>
    <div class="search-row">
      <input
        v-model="query"
        type="search"
        class="text-input"
        :placeholder="`Search by ${noun} title`"
        :aria-label="`Search by ${noun} title`"
        @keyup.enter="emit('search')"
      />
      <button
        type="button"
        class="secondary-button"
        :disabled="searching"
        @click="emit('search')"
      >
        {{ searching ? "Searching…" : "Search" }}
      </button>
    </div>
    <div v-if="results.length" class="metadata-results">
      <button
        v-for="result in results"
        :key="result.key"
        type="button"
        class="metadata-result"
        @click="emit('pick', result.key)"
      >
        <span>{{ result.title }}</span>
        <small
          >{{ result.provider
          }}<span v-if="result.detail"> · {{ result.detail }}</span></small
        >
      </button>
    </div>
    <p v-if="message" class="hint">{{ message }}</p>
    <ul v-if="warnings.length" class="provider-warnings">
      <li v-for="warning in warnings" :key="warning">{{ warning }}</li>
    </ul>
  </div>
</template>

<style scoped>
.search-row {
  display: flex;
  gap: 8px;
}

.search-row input {
  flex: 1;
  min-width: 0;
}

.metadata-results {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}

.metadata-result {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  width: 100%;
  padding: 9px 10px;
  text-align: left;
  color: var(--ui-text);
  background: var(--ui-border);
  border: 1px solid var(--ui-border);
  border-radius: 6px;
  cursor: pointer;
  font-family: inherit;
}

.metadata-result:hover {
  border-color: var(--ui-accent-text);
  background: #282828;
}

.metadata-result small {
  color: var(--ui-dim);
  font-size: 0.78rem;
}

.provider-warnings {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.provider-warnings li {
  color: #fca27a;
  font-size: 0.75rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
  min-width: 0;
}

.field span {
  font-size: 0.78rem;
  color: var(--ui-dim);
}

.field-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.field-row > .field {
  flex: 1 1 120px;
}

.text-input {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 8px 10px;
  font-size: 0.85rem;
  font-family: inherit;
  width: 100%;
  box-sizing: border-box;
}

.text-input:focus {
  outline: 2px solid var(--ui-accent-text);
  outline-offset: 1px;
}

.secondary-button {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  color: var(--ui-text);
  border-radius: var(--ui-radius-control);
  padding: 9px 14px;
  font-size: 0.85rem;
  cursor: pointer;
}
.hint {
  font-size: 0.78rem;
  color: var(--ui-dim);
  margin: 0;
}
</style>
