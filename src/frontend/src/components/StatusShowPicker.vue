<script setup lang="ts">
// Which statuses a library tab shows: each one is on (shown) or off (kept out).
import { computed, watch } from "vue";
import type { GameStatus } from "../types/game";
import { STATUS_OPTIONS } from "../utils/smartRuleFields";

const shown = defineModel<GameStatus[]>({ required: true });

const LABELS: Record<GameStatus, string> = {
  playing: "Playing",
  beaten: "Beaten",
  mastered: "Mastered",
  played: "Played",
  "on hold": "On hold",
  dropped: "Dropped",
  backlog: "Backlog",
  wishlist: "Wishlist",
};

const hidden = computed(() =>
  STATUS_OPTIONS.filter((s) => !shown.value.includes(s)),
);
// the parent hands the new list back a moment later, so quick clicks build on
// the last list sent rather than the one still showing
let latest = shown.value;
watch(shown, (v) => (latest = v));
function toggle(status: GameStatus) {
  const next = latest.includes(status)
    ? latest.filter((s) => s !== status)
    : [...latest, status];
  // kept in the usual order so saved tabs read the same every time
  latest = STATUS_OPTIONS.filter((s) => next.includes(s));
  shown.value = latest;
}
function setAll(on: boolean) {
  latest = on ? [...STATUS_OPTIONS] : [];
  shown.value = latest;
}
</script>

<template>
  <div class="ssp">
    <div class="ssp-head">
      <span>Statuses in this tab</span>
      <span class="ssp-quick">
        <button type="button" :disabled="!hidden.length" @click="setAll(true)">
          Show all
        </button>
        <button type="button" :disabled="!shown.length" @click="setAll(false)">
          Hide all
        </button>
      </span>
    </div>
    <div class="ssp-chips" role="group" aria-label="Statuses in this tab">
      <button
        v-for="s in STATUS_OPTIONS"
        :key="s"
        type="button"
        class="ssp-chip"
        :class="{ on: shown.includes(s) }"
        :aria-pressed="shown.includes(s)"
        @click="toggle(s)"
      >
        <svg
          v-if="shown.includes(s)"
          viewBox="0 0 24 24"
          width="12"
          height="12"
          fill="none"
          stroke="currentColor"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M5 12l5 5L19 7" />
        </svg>
        <svg
          v-else
          viewBox="0 0 24 24"
          width="12"
          height="12"
          fill="none"
          stroke="currentColor"
          stroke-width="3"
          stroke-linecap="round"
          aria-hidden="true"
        >
          <path d="M6 6l12 12M18 6L6 18" />
        </svg>
        {{ LABELS[s] }}
      </button>
    </div>
    <p class="ssp-note">
      <template v-if="!shown.length">Nothing is shown. Turn some on.</template>
      <template v-else-if="!hidden.length">Shows every status.</template>
      <template v-else>
        Not shown: {{ hidden.map((s) => LABELS[s]).join(", ") }}
      </template>
    </p>
  </div>
</template>

<style scoped>
.ssp {
  margin-bottom: 14px;
}
.ssp-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 0.82rem;
  color: var(--ui-text-soft);
}
.ssp-quick {
  display: flex;
  gap: 12px;
}
.ssp-quick button {
  background: none;
  border: none;
  padding: 0;
  color: var(--ui-accent);
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
}
.ssp-quick button:hover:not(:disabled) {
  text-decoration: underline;
}
.ssp-quick button:disabled {
  color: var(--ui-dim-2);
  cursor: default;
}
.ssp-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.ssp-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--ui-border);
  border-radius: 999px;
  background: transparent;
  color: var(--ui-dim-2);
  font: inherit;
  font-size: 12.5px;
  cursor: pointer;
}
.ssp-chip:hover {
  border-color: var(--ui-border-strong);
  color: var(--ui-text-soft);
}
.ssp-chip.on {
  border-color: var(--ui-accent-line);
  background: color-mix(in srgb, var(--ui-accent) 14%, transparent);
  color: var(--ui-heading);
}
.ssp-chip.on svg {
  color: var(--ui-accent);
}
.ssp-note {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--ui-dim-2);
}
</style>
