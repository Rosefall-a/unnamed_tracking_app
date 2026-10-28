<script setup lang="ts">
// The search box at the top of Settings: type a word, pick a page, and Settings
// opens it. Arrow keys move through the results, Enter opens one, Escape clears.
import { computed, ref } from "vue";
import { searchSettings } from "../../utils/settingsSearch";

const props = defineProps<{ isAdmin: boolean }>();
const emit = defineEmits<{ select: [id: string] }>();

const query = ref("");
const open = ref(false);
const active = ref(0);

const results = computed(() => searchSettings(query.value, props.isAdmin));

function pick(id: string) {
  emit("select", id);
  query.value = "";
  open.value = false;
  active.value = 0;
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    query.value = "";
    open.value = false;
    return;
  }
  if (!results.value.length) return;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    active.value = (active.value + 1) % results.value.length;
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    active.value =
      (active.value - 1 + results.value.length) % results.value.length;
  } else if (e.key === "Enter") {
    e.preventDefault();
    pick(results.value[active.value].id);
  }
}

function onInput() {
  open.value = true;
  active.value = 0;
}

// a click on a result lands before the box loses focus and closes the list
function onBlur() {
  window.setTimeout(() => (open.value = false), 120);
}
</script>

<template>
  <div class="settings-search" role="search">
    <input
      v-model="query"
      type="search"
      class="settings-search-input"
      placeholder="Search settings"
      aria-label="Search settings"
      autocomplete="off"
      role="combobox"
      aria-controls="settings-search-results"
      :aria-expanded="open && results.length > 0"
      @input="onInput"
      @focus="open = true"
      @blur="onBlur"
      @keydown="onKeydown"
    />
    <ul
      v-if="open && query.trim()"
      id="settings-search-results"
      class="settings-search-results"
      role="listbox"
    >
      <li
        v-for="(entry, index) in results"
        :key="entry.id"
        role="option"
        :aria-selected="index === active"
        :class="{ active: index === active }"
        @mousedown.prevent="pick(entry.id)"
        @mousemove="active = index"
      >
        <span class="result-label">{{ entry.label }}</span>
        <span class="result-group">{{ entry.group }}</span>
      </li>
      <li v-if="!results.length" class="none" role="presentation">
        No settings match "{{ query.trim() }}"
      </li>
    </ul>
  </div>
</template>

<style scoped>
.settings-search {
  position: relative;
  width: min(300px, 100%);
}
.settings-search-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 12px;
  border: 1px solid #2b2b2b;
  border-radius: 8px;
  background: #151515;
  color: #e5e5e5;
  font-size: 0.85rem;
}
.settings-search-input::placeholder {
  color: #777;
}
.settings-search-input:focus {
  border-color: #d68a34;
  outline: none;
}
.settings-search-results {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 50;
  margin: 0;
  padding: 4px;
  list-style: none;
  border: 1px solid #2b2b2b;
  border-radius: 10px;
  background: #1a1a1a;
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.5);
}
.settings-search-results li {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 0.85rem;
  color: #e5e5e5;
  cursor: pointer;
}
.settings-search-results li.active {
  background: rgba(214, 138, 52, 0.16);
}
.settings-search-results li.none {
  color: #888;
  cursor: default;
}
.result-group {
  flex: none;
  font-size: 0.7rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #777;
}
</style>
