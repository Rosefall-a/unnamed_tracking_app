<script setup lang="ts">
// Your score for a game. Same pill and same card as the Media score picker,
// but a game is scored in four parts, so the panel holds four boxes
// (Atmosphere, Story, Gameplay, Sound), each 0 to 10. The pill shows the
// total, which is what the rest of the game pages use. Enter or Save
// stores all four; Escape or a click outside closes.
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from "vue";
import type { GameRatings } from "../services/games";

const props = defineProps<{ modelValue: GameRatings }>();
const emit = defineEmits<{ change: [value: GameRatings] }>();

const FIELDS: { key: keyof GameRatings; label: string }[] = [
  { key: "ratingOverall", label: "Atmosphere" },
  { key: "ratingStory", label: "Story" },
  { key: "ratingGameplay", label: "Gameplay" },
  { key: "ratingSound", label: "Sound" },
];

const open = ref(false);
const anchor = ref<HTMLElement | null>(null);
const firstInput = ref<HTMLInputElement[] | null>(null);
const panelStyle = ref<{ top: string; left: string }>({
  top: "0px",
  left: "0px",
});
const drafts = ref<Record<keyof GameRatings, string>>({
  ratingOverall: "",
  ratingStory: "",
  ratingGameplay: "",
  ratingSound: "",
});
const invalid = ref<Partial<Record<keyof GameRatings, boolean>>>({});

const given = computed(() =>
  FIELDS.map((f) => props.modelValue[f.key]).filter(
    (v): v is number => v !== null,
  ),
);
const total = computed(() => given.value.reduce((a, b) => a + b, 0));
const label = computed(() =>
  given.value.length === 0 ? "Rate" : `★ ${total.value.toFixed(1)}`,
);

async function toggle() {
  open.value = !open.value;
  if (!open.value || !anchor.value) return;
  const rect = anchor.value.getBoundingClientRect();
  panelStyle.value = {
    top: `${rect.bottom + 10}px`,
    left: `${Math.max(8, Math.min(rect.left, window.innerWidth - 248))}px`,
  };
  for (const f of FIELDS) {
    const v = props.modelValue[f.key];
    drafts.value[f.key] = v === null ? "" : String(v);
  }
  invalid.value = {};
  await nextTick();
  const el = firstInput.value?.[0];
  el?.focus();
  el?.setSelectionRange(el.value.length, el.value.length);
}

function save() {
  const next = {} as GameRatings;
  const bad: Partial<Record<keyof GameRatings, boolean>> = {};
  for (const f of FIELDS) {
    const raw = drafts.value[f.key].trim().replace(",", ".");
    if (raw === "") {
      next[f.key] = null;
      continue;
    }
    const n = Number(raw);
    if (Number.isNaN(n) || n < 0 || n > 10) {
      bad[f.key] = true;
      continue;
    }
    next[f.key] = Math.round(n * 10) / 10;
  }
  invalid.value = bad;
  if (Object.keys(bad).length) return;
  emit("change", next);
  open.value = false;
}
function clear() {
  emit("change", {
    ratingOverall: null,
    ratingStory: null,
    ratingGameplay: null,
    ratingSound: null,
  });
  open.value = false;
}

function onDocumentClick(e: MouseEvent) {
  if (!open.value) return;
  const target = e.target as HTMLElement;
  if (anchor.value?.contains(target) || target.closest?.(".rating-panel"))
    return;
  open.value = false;
}
function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") open.value = false;
}
onMounted(() => {
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onKey);
});
onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onKey);
});
</script>

<template>
  <button
    ref="anchor"
    type="button"
    class="rating-pill"
    :class="{ unrated: given.length === 0, open }"
    title="Set your score"
    aria-haspopup="dialog"
    :aria-expanded="open"
    @click="toggle"
  >
    {{ label }}
  </button>

  <Teleport to="body">
    <Transition name="pop">
      <form
        v-if="open"
        class="rating-panel"
        role="dialog"
        aria-label="Your score"
        :style="panelStyle"
        @submit.prevent="save"
      >
        <div class="panel-head">
          <span class="panel-title">Your score</span>
          <span v-if="given.length" class="panel-total"
            >{{ total.toFixed(1) }} / {{ given.length * 10 }}</span
          >
        </div>
        <div class="field-grid">
          <label v-for="f in FIELDS" :key="f.key" class="field">
            <span class="field-label">{{ f.label }}</span>
            <input
              ref="firstInput"
              v-model="drafts[f.key]"
              class="score-input"
              :class="{ invalid: invalid[f.key] }"
              type="text"
              inputmode="decimal"
              autocomplete="off"
              placeholder="0 to 10"
              maxlength="4"
              @input="invalid[f.key] = false"
            />
          </label>
        </div>
        <p v-if="Object.keys(invalid).length" class="hint bad">
          Scores run from 0 to 10.
        </p>
        <div class="panel-actions">
          <button
            v-if="given.length"
            type="button"
            class="clear-btn"
            @click="clear"
          >
            Clear
          </button>
          <button type="submit" class="save-btn">Save</button>
        </div>
      </form>
    </Transition>
  </Teleport>
</template>

<style scoped>
.rating-pill {
  background-color: color-mix(in srgb, var(--ui-text) 6%, transparent);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d68a34' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 12px;
  border: 1px solid color-mix(in srgb, var(--ui-accent) 40%, transparent);
  border-radius: var(--ui-radius-control);
  line-height: 1.25;
  padding: 4px 26px 4px 11px;
  font-family: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--ui-accent-text);
  cursor: pointer;
  transition: background-color 0.15s ease;
}
.rating-pill:hover,
.rating-pill.open {
  background-color: color-mix(in srgb, var(--ui-accent) 16%, transparent);
}
.rating-pill.unrated {
  color: var(--ui-dim);
  border-color: color-mix(in srgb, var(--ui-text) 14%, transparent);
}
.rating-panel {
  position: fixed;
  z-index: var(--ui-z-popover);
  width: 240px;
  max-width: calc(100vw - 16px);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-dialog);
  padding: 12px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
  font-family: var(--ui-font-family);
}
.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.panel-title {
  font-size: 0.72rem;
  font-weight: var(--ui-weight-title);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ui-dim);
}
.panel-total {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--ui-accent-text);
  font-variant-numeric: tabular-nums;
}
.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.field-label {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--ui-dim);
}
.score-input {
  box-sizing: border-box;
  width: 100%;
  height: 40px;
  background: var(--ui-bg);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  color: var(--ui-accent-text);
  font: inherit;
  font-size: 1.1rem;
  font-weight: var(--ui-weight-title);
  text-align: center;
  font-variant-numeric: tabular-nums;
  transition: border-color 0.15s ease;
}
.score-input::placeholder {
  color: #4a4a4a;
  font-size: 0.78rem;
  font-weight: 600;
}
.score-input:focus {
  outline: none;
  border-color: var(--ui-accent-text);
}
.score-input.invalid {
  border-color: var(--ui-error);
}
.hint {
  margin: 0;
  font-size: 0.72rem;
}
.hint.bad {
  color: var(--ui-error);
}
.panel-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}
.save-btn {
  height: 30px;
  padding: 0 14px;
  border: none;
  border-radius: var(--ui-radius-control);
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}
.save-btn:hover {
  filter: brightness(1.08);
}
.clear-btn {
  height: 30px;
  padding: 0 10px;
  border: none;
  border-radius: var(--ui-radius-control);
  background: none;
  color: var(--ui-dim);
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}
.clear-btn:hover {
  color: var(--ui-error);
  background: rgba(229, 115, 115, 0.08);
}
.pop-enter-active,
.pop-leave-active {
  transition:
    opacity 0.12s ease,
    transform 0.12s ease;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
