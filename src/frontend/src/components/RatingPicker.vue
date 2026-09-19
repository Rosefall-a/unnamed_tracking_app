<script setup lang="ts">
// Your score. Click the pill in the hero and a small panel opens (same
// card style as the Lists and Rewatch panels beside it) with one text
// box: type a score from 0 to 10 (a decimal like 8.5 is fine) and press
// Enter or Save. Clear removes it. Escape or a click outside closes.
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from "vue";

const props = defineProps<{ modelValue: number | null }>();
const emit = defineEmits<{ change: [value: number | null] }>();

const open = ref(false);
const anchor = ref<HTMLElement | null>(null);
const inputEl = ref<HTMLInputElement | null>(null);
const panelStyle = ref<{ top: string; left: string }>({ top: "0px", left: "0px" });
const text = ref("");
const invalid = ref(false);

const label = computed(() =>
  props.modelValue === null ? "Rate" : `★ ${Number.isInteger(props.modelValue) ? props.modelValue.toFixed(1) : props.modelValue}`,
);

async function toggle() {
  open.value = !open.value;
  if (!open.value || !anchor.value) return;
  const rect = anchor.value.getBoundingClientRect();
  panelStyle.value = {
    top: `${rect.bottom + 10}px`,
    left: `${Math.max(8, Math.min(rect.left, window.innerWidth - 208))}px`,
  };
  text.value = props.modelValue === null ? "" : String(props.modelValue);
  invalid.value = false;
  await nextTick();
  // focus only: the cursor lands after the current number, nothing is
  // pre-selected, so typing adds to it instead of replacing it
  const el = inputEl.value;
  el?.focus();
  el?.setSelectionRange(el.value.length, el.value.length);
}

function save() {
  const raw = text.value.trim().replace(",", ".");
  if (raw === "") {
    emit("change", null);
    open.value = false;
    return;
  }
  const n = Number(raw);
  if (Number.isNaN(n) || n < 0 || n > 10) {
    invalid.value = true;
    return;
  }
  emit("change", Math.round(n * 10) / 10);
  open.value = false;
}
function clear() {
  emit("change", null);
  open.value = false;
}

function onDocumentClick(e: MouseEvent) {
  if (!open.value) return;
  const target = e.target as HTMLElement;
  if (anchor.value?.contains(target) || target.closest?.(".rating-panel")) return;
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
    :class="{ unrated: modelValue === null, open }"
    title="Set your score"
    aria-haspopup="dialog"
    :aria-expanded="open"
    @click="toggle"
  >
    {{ label }}
  </button>

  <Teleport to="body">
    <Transition name="pop">
      <form v-if="open" class="rating-panel" role="dialog" aria-label="Your score" :style="panelStyle" @submit.prevent="save">
        <label class="panel-title" for="rating-input">Your score</label>
        <input
          id="rating-input"
          ref="inputEl"
          v-model="text"
          class="score-input"
          :class="{ invalid }"
          type="text"
          inputmode="decimal"
          autocomplete="off"
          placeholder="0 to 10"
          maxlength="4"
          @input="invalid = false"
        />
        <p v-if="invalid" class="hint bad">Enter a number from 0 to 10.</p>
        <div class="panel-actions">
          <button v-if="modelValue !== null" type="button" class="clear-btn" @click="clear">Clear</button>
          <button type="submit" class="save-btn">Save</button>
        </div>
      </form>
    </Transition>
  </Teleport>
</template>

<style scoped>
.rating-pill {
  background-color: rgba(255, 255, 255, 0.06);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d68a34' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 12px;
  border: 1px solid rgba(214, 138, 52, 0.4);
  border-radius: 7px;
  line-height: 1.25;
  padding: 4px 26px 4px 11px;
  font-family: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  color: #d68a34;
  cursor: pointer;
  transition: background-color 0.15s ease;
}
.rating-pill:hover,
.rating-pill.open {
  background-color: rgba(214, 138, 52, 0.16);
}
.rating-pill.unrated {
  color: #9c9c9c;
  border-color: rgba(255, 255, 255, 0.14);
}
.rating-panel {
  position: fixed;
  z-index: var(--ui-z-popover);
  width: 200px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #171717;
  border: 1px solid #2b2b2b;
  border-radius: 14px;
  padding: 12px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
  font-family: system-ui, sans-serif;
}
.panel-title {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #9c9c9c;
}
.score-input {
  box-sizing: border-box;
  width: 100%;
  height: 40px;
  background: #0d0d0d;
  border: 1px solid #2b2b2b;
  border-radius: 8px;
  color: #d68a34;
  font: inherit;
  font-size: 1.25rem;
  font-weight: 800;
  text-align: center;
  font-variant-numeric: tabular-nums;
  transition: border-color 0.15s ease;
}
.score-input::placeholder {
  color: #4a4a4a;
  font-size: 0.85rem;
  font-weight: 600;
}
.score-input:focus {
  outline: none;
  border-color: #d68a34;
}
.score-input.invalid {
  border-color: #e57373;
}
.hint {
  margin: 0;
  font-size: 0.72rem;
}
.hint.bad {
  color: #e57373;
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
  border-radius: 8px;
  background: #d68a34;
  color: #14100a;
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
  border-radius: 8px;
  background: none;
  color: #9c9c9c;
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}
.clear-btn:hover {
  color: #e57373;
  background: rgba(229, 115, 115, 0.08);
}
.pop-enter-active,
.pop-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
