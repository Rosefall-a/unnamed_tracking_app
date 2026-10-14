<script setup lang="ts">
// A small pill on a game's page when it may be the same game as another entry. The
// page places it (it floats in the hero), so it never changes the layout around it.
import { ref, watch } from "vue";
import DuplicateReviewDialog from "./DuplicateReviewDialog.vue";
import { fetchMatchesForGame, type GameMatch } from "../services/gameMatches";

const props = defineProps<{ gameId: string }>();
const emit = defineEmits<{ resolved: [] }>();

const matches = ref<GameMatch[]>([]);
const reviewing = ref<GameMatch | null>(null);

async function load() {
  try {
    matches.value = await fetchMatchesForGame(props.gameId);
  } catch {
    matches.value = [];
  }
}
watch(() => props.gameId, load, { immediate: true });

async function onResolved() {
  reviewing.value = null;
  await load();
  emit("resolved");
}

function otherTitle(match: GameMatch): string {
  return match.original.id === props.gameId
    ? `${match.steam.title} (Steam)`
    : `${match.original.title} (yours)`;
}
</script>

<template>
  <div v-if="matches.length" class="dup-notice" role="status">
    <svg
      class="dup-icon"
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15V6a2 2 0 0 1 2-2h9" />
    </svg>
    <span class="dup-notice-text">
      <strong>Possible duplicate</strong>
      <span class="dup-notice-other">of {{ otherTitle(matches[0]) }}</span>
    </span>
    <button type="button" @click="reviewing = matches[0]">Review</button>
    <DuplicateReviewDialog
      v-if="reviewing"
      :match="reviewing"
      @close="reviewing = null"
      @resolved="onResolved"
    />
  </div>
</template>

<style scoped>
.dup-notice {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 100%;
  box-sizing: border-box;
  padding: 6px 6px 6px 12px;
  border: 1px solid rgba(214, 138, 52, 0.45);
  border-radius: 999px;
  background: rgba(20, 14, 8, 0.82);
  backdrop-filter: blur(8px);
  color: #e5e5e5;
  font-size: 0.8rem;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
}
.dup-icon {
  flex: none;
  color: #d68a34;
}
.dup-notice-text {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}
.dup-notice-text strong {
  flex: none;
  color: #fff;
  font-weight: 700;
}
.dup-notice-other {
  min-width: 0;
  overflow: hidden;
  color: #b5b5b5;
  text-overflow: ellipsis;
}
.dup-notice button {
  flex: none;
  padding: 5px 14px;
  border: 0;
  border-radius: 999px;
  background: #d68a34;
  color: #0d0d0d;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
}
.dup-notice button:hover {
  background: #e29a48;
}
.dup-notice button:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 2px;
}
@media (max-width: 420px) {
  .dup-notice-other {
    display: none;
  }
}
</style>
