<script setup lang="ts">
import { ref, computed, watch, useId, onBeforeUnmount, nextTick } from "vue";

const props = defineProps<{
  modelValue: string;
  options: string[];
  placeholder: string;
  allLabel?: string;
  // A second, larger pool only searched once the user starts typing, keeps
  // the default dropdown short while still making everything findable.
  extraOptions?: string[];
  extraLabel?: string;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const query = ref("");
const open = ref(false);
const listId = useId();
const activeIndex = ref(0);
let blurTimer: ReturnType<typeof setTimeout> | undefined;

const displayLabel = computed(() =>
  props.modelValue === "all" ? (props.allLabel ?? "All") : props.modelValue,
);

watch(
  () => props.modelValue,
  () => {
    query.value = "";
  },
);

const filteredOptions = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return props.options;
  return props.options.filter((o) => o.toLowerCase().includes(q));
});

const filteredExtraOptions = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q || !props.extraOptions) return [];
  return props.extraOptions.filter((o) => o.toLowerCase().includes(q));
});
const values = computed(() => [
  "all",
  ...filteredOptions.value,
  ...filteredExtraOptions.value,
]);
watch(query, () => {
  activeIndex.value = 0;
});
onBeforeUnmount(() => clearTimeout(blurTimer));

async function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    event.preventDefault();
    open.value = false;
    query.value = "";
  } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    if (!open.value) {
      open.value = true;
      activeIndex.value = 0;
    } else
      activeIndex.value =
        (activeIndex.value +
          (event.key === "ArrowDown" ? 1 : -1) +
          values.value.length) %
        values.value.length;
    await nextTick();
    document
      .getElementById(`${listId}-${activeIndex.value}`)
      ?.scrollIntoView({ block: "nearest" });
  } else if (event.key === "Enter" && open.value) {
    event.preventDefault();
    select(values.value[activeIndex.value] ?? "all");
  }
}

function select(value: string) {
  emit("update:modelValue", value);
  query.value = "";
  open.value = false;
  clearTimeout(blurTimer);
}

function onFocus() {
  clearTimeout(blurTimer);
  open.value = true;
  query.value = "";
  activeIndex.value = Math.max(0, values.value.indexOf(props.modelValue));
}

function onBlur() {
  blurTimer = setTimeout(() => {
    open.value = false;
    query.value = "";
  }, 150);
}
</script>

<template>
  <div class="combobox">
    <input
      type="text"
      class="combobox-input"
      :placeholder="placeholder"
      :aria-label="placeholder"
      role="combobox"
      aria-autocomplete="list"
      :aria-expanded="open"
      :aria-controls="listId"
      :aria-activedescendant="open ? `${listId}-${activeIndex}` : undefined"
      :value="open ? query : displayLabel"
      @input="
        open = true;
        query = ($event.target as HTMLInputElement).value;
      "
      @keydown="onKeydown"
      @focus="onFocus"
      @blur="onBlur"
    />
    <div
      v-if="open"
      :id="listId"
      class="combobox-menu"
      role="listbox"
      :aria-label="placeholder"
    >
      <button
        :id="`${listId}-0`"
        type="button"
        class="combobox-option"
        role="option"
        tabindex="-1"
        :aria-selected="modelValue === 'all'"
        :class="{
          highlighted: activeIndex === 0,
          active: modelValue === 'all',
        }"
        @pointerdown.prevent
        @click="select('all')"
      >
        {{ allLabel ?? "All" }}
      </button>
      <button
        v-for="(opt, index) in filteredOptions"
        :key="opt"
        :id="`${listId}-${index + 1}`"
        type="button"
        class="combobox-option"
        role="option"
        tabindex="-1"
        :aria-selected="opt === modelValue"
        :class="{
          active: opt === modelValue,
          highlighted: activeIndex === index + 1,
        }"
        @pointerdown.prevent
        @click="select(opt)"
      >
        {{ opt }}
      </button>
      <div v-if="filteredExtraOptions.length" class="combobox-group-label">
        {{ extraLabel ?? "More" }}
      </div>
      <button
        v-for="(opt, index) in filteredExtraOptions"
        :key="opt"
        :id="`${listId}-${filteredOptions.length + index + 1}`"
        type="button"
        class="combobox-option"
        role="option"
        tabindex="-1"
        :aria-selected="opt === modelValue"
        :class="{
          active: opt === modelValue,
          highlighted: activeIndex === filteredOptions.length + index + 1,
        }"
        @pointerdown.prevent
        @click="select(opt)"
      >
        {{ opt }}
      </button>
      <div
        v-if="!filteredOptions.length && !filteredExtraOptions.length"
        class="combobox-empty"
      >
        No matches
      </div>
    </div>
  </div>
</template>

<style scoped>
.combobox {
  position: relative;
}
.combobox-input {
  min-height: var(--ui-control-height);
  box-sizing: border-box;
  width: 160px;
  max-width: 100%;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 0 14px;
  font: inherit;
  font-size: 13px;
}
.combobox-input::placeholder {
  color: var(--ui-faint);
}
.combobox-input:focus {
  border-color: var(--ui-accent);
}
.combobox-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  width: 200px;
  max-height: 240px;
  overflow-y: auto;
  box-sizing: border-box;
  background: var(--ui-popover);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  box-shadow: var(--ui-elevation);
  z-index: 50;
  display: flex;
  flex-direction: column;
  padding: 4px;
}
.combobox-option {
  background: none;
  border: none;
  color: var(--ui-text);
  min-height: var(--ui-control-height);
  flex-shrink: 0;
  text-align: left;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  text-transform: capitalize;
}
.combobox-option:hover,
.combobox-option.highlighted {
  background: var(--ui-surface-2);
  color: var(--ui-text);
}
.combobox-option.active {
  background: var(--ui-accent-soft);
  color: var(--ui-accent-text);
}
.combobox-empty {
  color: var(--ui-dim);
  font-size: 12px;
  padding: 8px 10px;
}
.combobox-group-label {
  color: var(--ui-dim);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
  padding: 8px 10px 4px;
}
</style>
