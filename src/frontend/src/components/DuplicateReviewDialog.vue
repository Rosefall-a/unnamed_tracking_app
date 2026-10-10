<script setup lang="ts">
// Two entries that may be the same game, side by side, and what to do about it.
import { computed, ref } from "vue";
import {
  keepBoth,
  mergeMatch,
  type GameMatch,
  type MatchGame,
  type Prefer,
} from "../services/gameMatches";

const props = defineProps<{ match: GameMatch }>();
const emit = defineEmits<{ close: []; resolved: [match: GameMatch] }>();

const SIDES = ["original", "steam"] as const;
const prefer = ref<Prefer>("mine");
const busy = ref(false);
const error = ref<string | null>(null);

function playtime(seconds: number): string {
  if (!seconds) return "–";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function rows(game: MatchGame): [string, string][] {
  return [
    ["Source", game.source ?? "Added by hand"],
    [
      "Status",
      game.status.charAt(0).toUpperCase() +
        game.status.slice(1).replace(/_/g, " "),
    ],
    ["Rating", game.rating === null ? "–" : String(game.rating)],
    ["Playtime", playtime(game.playtimeSeconds)],
    ["Achievements", game.achievements ? String(game.achievements) : "–"],
    ["Notes", game.notes ? String(game.notes) : "–"],
    ["Screenshots", game.screenshots ? String(game.screenshots) : "–"],
  ];
}

// each attribute once, with what each entry has for it
const compared = computed(() =>
  rows(props.match.original).map(([label, mine], index) => ({
    label,
    original: mine,
    steam: rows(props.match.steam)[index][1],
  })),
);

async function run(action: () => Promise<GameMatch>) {
  busy.value = true;
  error.value = null;
  try {
    emit("resolved", await action());
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Something went wrong.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="dup-overlay" @click.self="emit('close')">
    <div class="dup-dialog" role="dialog" aria-label="Possible duplicate">
      <h2>Is this the same game?</h2>
      <p class="dup-lead">
        A Steam sync found
        <strong>{{ props.match.steam.title }}</strong> and you already have
        <strong>{{ props.match.original.title }}</strong
        >. Nothing changes until you choose.
      </p>

      <div
        class="dup-compare"
        role="table"
        aria-label="The two entries compared"
      >
        <div class="dup-corner" role="presentation"></div>
        <div
          v-for="side in SIDES"
          :key="side"
          class="dup-head"
          role="columnheader"
        >
          <span class="dup-tag">{{
            side === "original" ? "Your entry" : "From Steam"
          }}</span>
          <div
            class="dup-cover"
            :style="{ backgroundImage: `url(${props.match[side].coverUrl})` }"
          ></div>
          <span class="dup-title">{{ props.match[side].title }}</span>
        </div>
        <template v-for="row in compared" :key="row.label">
          <div class="dup-label" role="rowheader">{{ row.label }}</div>
          <div
            v-for="side in SIDES"
            :key="side"
            class="dup-value"
            :class="{ empty: row[side] === '–' }"
            role="cell"
          >
            {{ row[side] }}
          </div>
        </template>
      </div>

      <fieldset class="dup-choice">
        <legend>If you merge, whose details win where both have one?</legend>
        <label :class="{ on: prefer === 'mine' }">
          <input v-model="prefer" type="radio" value="mine" />
          My details
        </label>
        <label :class="{ on: prefer === 'steam' }">
          <input v-model="prefer" type="radio" value="steam" />
          Steam's details
        </label>
      </fieldset>
      <p class="dup-note">
        Merging keeps your entry, with all its notes, screenshots and files. It
        gains the Steam link, the achievements and the playtime. The Steam copy
        goes to the trash, and you can undo this from Settings, Library.
      </p>

      <p v-if="error" class="dup-error">{{ error }}</p>
      <div class="dup-actions">
        <button type="button" class="dup-later" @click="emit('close')">
          Decide later
        </button>
        <button
          type="button"
          class="dup-secondary"
          :disabled="busy"
          @click="run(() => keepBoth(props.match.id))"
        >
          Keep both
        </button>
        <button
          type="button"
          class="dup-primary"
          :disabled="busy"
          @click="run(() => mergeMatch(props.match.id, prefer))"
        >
          {{ busy ? "Working…" : "Merge" }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dup-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.7);
}
.dup-dialog {
  width: min(560px, 100%);
  max-height: 92vh;
  overflow-y: auto;
  padding: 24px;
  border: 1px solid #2b2b2b;
  border-radius: 14px;
  background: #1a1a1a;
  color: #e5e5e5;
}
.dup-dialog h2 {
  margin: 0 0 6px;
  font-size: 1.15rem;
  color: #fff;
}
.dup-lead {
  margin: 0 0 18px;
  font-size: 0.86rem;
  line-height: 1.5;
  color: #b5b5b5;
}
.dup-lead strong {
  color: #fff;
}
.dup-compare {
  display: grid;
  grid-template-columns: minmax(84px, 0.8fr) 1fr 1fr;
  align-items: center;
  border: 1px solid #2b2b2b;
  border-radius: 10px;
  background: #111;
  overflow: hidden;
}
.dup-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 14px 8px 12px;
  text-align: center;
  border-bottom: 1px solid #2b2b2b;
}
.dup-corner {
  border-bottom: 1px solid #2b2b2b;
  align-self: stretch;
}
.dup-tag {
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #d68a34;
}
.dup-cover {
  width: 60px;
  aspect-ratio: 2 / 3;
  border-radius: 6px;
  background: #222 center / cover no-repeat;
  box-shadow: 0 8px 18px -6px rgba(0, 0, 0, 0.6);
}
.dup-title {
  max-width: 100%;
  font-size: 0.85rem;
  font-weight: 600;
  color: #fff;
  overflow-wrap: anywhere;
}
.dup-label,
.dup-value {
  padding: 9px 12px;
  font-size: 0.8rem;
  border-bottom: 1px solid #1c1c1c;
  align-self: stretch;
  display: flex;
  align-items: center;
}
.dup-label {
  color: #8a8a8a;
}
.dup-value {
  justify-content: center;
  text-align: center;
  color: #e5e5e5;
  font-variant-numeric: tabular-nums;
}
.dup-value.empty {
  color: #4a4a4a;
}
.dup-compare > :nth-last-child(-n + 3) {
  border-bottom: 0;
}
.dup-choice {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 18px 0 0;
  padding: 0;
  border: 0;
}
.dup-choice legend {
  margin-bottom: 8px;
  padding: 0;
  font-size: 0.8rem;
  color: #b5b5b5;
}
.dup-choice label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid #2b2b2b;
  border-radius: 8px;
  font-size: 0.84rem;
  cursor: pointer;
}
.dup-choice label.on {
  border-color: #d68a34;
  background: rgba(214, 138, 52, 0.12);
}
.dup-choice input {
  accent-color: #d68a34;
}
.dup-note {
  margin: 12px 0 0;
  font-size: 0.78rem;
  line-height: 1.5;
  color: #8a8a8a;
}
.dup-error {
  margin: 12px 0 0;
  font-size: 0.82rem;
  color: #f87171;
}
.dup-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
.dup-actions button {
  padding: 9px 18px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}
.dup-later {
  margin-right: auto;
  border: 0;
  background: none;
  color: #8a8a8a;
}
.dup-secondary {
  border: 1px solid #3a3a3a;
  background: transparent;
  color: #e5e5e5;
}
.dup-primary {
  border: 1px solid #d68a34;
  background: #d68a34;
  color: #0d0d0d;
}
.dup-actions button:disabled {
  opacity: 0.6;
  cursor: default;
}
.dup-actions button:focus-visible {
  outline: 2px solid #d68a34;
  outline-offset: 2px;
}
</style>
