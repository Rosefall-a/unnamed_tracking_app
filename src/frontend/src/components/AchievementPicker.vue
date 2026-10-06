<script setup lang="ts">
// Pick the achievement a file belongs to. A button shows the current choice;
// it opens a small searchable list (type to narrow, click to choose, Enter
// takes the first match), so tying a screenshot to one of 300 achievements
// takes a few keystrokes instead of scrolling a dropdown.
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from "vue";
import type { Achievement } from "../types/game";

const props = defineProps<{
  modelValue: string | null;
  achievements: Achievement[];
  // open the list above the button (used at the bottom of the viewer)
  up?: boolean;
  compact?: boolean;
}>();
const emit = defineEmits<{ change: [id: string | null] }>();

const open = ref(false);
const query = ref("");
const anchor = ref<HTMLElement | null>(null);
const input = ref<HTMLInputElement | null>(null);
const style = ref<Record<string, string>>({});

const current = computed(
  () => props.achievements.find((a) => a.id === props.modelValue) ?? null,
);
const matches = computed(() => {
  const q = query.value.trim().toLowerCase();
  const list = q
    ? props.achievements.filter((a) => a.name.toLowerCase().includes(q))
    : props.achievements;
  return list.slice(0, 60);
});

async function toggle() {
  open.value = !open.value;
  if (!open.value || !anchor.value) return;
  query.value = "";
  const r = anchor.value.getBoundingClientRect();
  const width = Math.min(320, window.innerWidth - 16);
  const left = Math.max(8, Math.min(r.left, window.innerWidth - width - 8));
  style.value = props.up
    ? {
        left: `${left}px`,
        width: `${width}px`,
        bottom: `${window.innerHeight - r.top + 8}px`,
      }
    : { left: `${left}px`, width: `${width}px`, top: `${r.bottom + 8}px` };
  await nextTick();
  input.value?.focus();
}
function choose(id: string | null) {
  emit("change", id);
  open.value = false;
}
function onEnter() {
  if (matches.value[0]) choose(matches.value[0].id);
}

function onDocumentClick(e: MouseEvent) {
  if (!open.value) return;
  const t = e.target as HTMLElement;
  if (anchor.value?.contains(t) || t.closest?.(".ap-panel")) return;
  open.value = false;
}
function onKey(e: KeyboardEvent) {
  if (open.value && e.key === "Escape") {
    e.stopPropagation();
    open.value = false;
  }
}
onMounted(() => {
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onKey, true);
});
onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onKey, true);
});
</script>

<template>
  <button
    ref="anchor"
    type="button"
    class="ap-btn"
    :class="{ set: !!current, compact, open }"
    aria-haspopup="listbox"
    :aria-expanded="open"
    @click="toggle"
  >
    <svg
      viewBox="0 0 24 24"
      width="13"
      height="13"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M8 4h8v5a4 4 0 0 1-8 0z" />
      <path d="M8 4H5a2 2 0 0 0 0 4h1.5M16 4h3a2 2 0 0 1 0 4h-1.5" />
      <path d="M12 13v3" />
      <path d="M9 20h6" />
      <path d="M10 16.5h4l.8 3.5H9.2z" />
    </svg>
    <span class="ap-label">{{
      current ? current.name : "Tie to achievement"
    }}</span>
  </button>

  <Teleport to="body">
    <div v-if="open" class="ap-panel" :style="style" role="listbox">
      <input
        ref="input"
        v-model="query"
        type="search"
        class="ap-search"
        placeholder="Search achievements"
        aria-label="Search achievements"
        @keydown.enter.prevent="onEnter"
      />
      <ul class="ap-list">
        <li v-if="current">
          <button type="button" class="ap-none" @click="choose(null)">
            Remove the tie to “{{ current.name }}”
          </button>
        </li>
        <li v-for="a in matches" :key="a.id">
          <button
            type="button"
            class="ap-item"
            :class="{ on: a.id === modelValue }"
            @click="choose(a.id)"
          >
            <span
              class="ap-icon"
              :style="a.iconUrl ? { backgroundImage: `url(${a.iconUrl})` } : {}"
            ></span>
            <span class="ap-name">{{ a.name }}</span>
          </button>
        </li>
        <li v-if="!matches.length" class="ap-empty">No achievement matches.</li>
      </ul>
    </div>
  </Teleport>
</template>

<style scoped>
.ap-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  max-width: 100%;
  height: 38px;
  padding: 0 12px;
  background: var(--ui-surface, var(--ui-surface));
  border: 1px solid var(--ui-border, var(--ui-border));
  border-radius: var(--ui-radius-control, 8px);
  color: var(--ui-dim);
  font-family: inherit;
  font-size: 0.85rem;
  cursor: pointer;
}
.ap-btn.compact {
  height: 30px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}
.ap-btn:hover,
.ap-btn.open {
  border-color: var(--ui-border-strong);
  color: var(--ui-text);
}
.ap-btn.set {
  color: var(--ui-accent-text);
  background: color-mix(in srgb, var(--ui-accent) 12%, transparent);
  border-color: color-mix(in srgb, var(--ui-accent) 40%, transparent);
}
.ap-btn svg {
  flex-shrink: 0;
}
.ap-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ap-panel {
  position: fixed;
  z-index: var(--ui-z-popover, 350);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-dialog);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
  font-family: var(--ui-font-family);
}
.ap-search {
  height: 36px;
  box-sizing: border-box;
  padding: 0 12px;
  background: var(--ui-bg);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  font: inherit;
  font-size: 0.85rem;
}
.ap-search:focus {
  outline: none;
  border-color: var(--ui-accent-text);
}
.ap-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ap-item,
.ap-none {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 6px 8px;
  font-family: inherit;
  font-size: 0.82rem;
  cursor: pointer;
}
.ap-item:hover,
.ap-none:hover {
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
}
.ap-item.on {
  color: var(--ui-accent-text);
  background: color-mix(in srgb, var(--ui-accent) 12%, transparent);
}
.ap-none {
  color: var(--ui-error);
  font-size: 0.78rem;
}
.ap-icon {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: 6px;
  background: var(--ui-surface-2) center / cover no-repeat;
}
.ap-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ap-empty {
  padding: 10px 8px;
  color: var(--ui-faint);
  font-size: 0.8rem;
}
</style>
