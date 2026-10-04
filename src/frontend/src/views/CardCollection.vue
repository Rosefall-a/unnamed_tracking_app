<script setup lang="ts">
import PageHeader from "../components/PageHeader.vue";
import UiModal from "../components/UiModal.vue";
import AccountChip from "../components/AccountChip.vue";
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { listCards, createCard } from "../services/cards";
import { fetchGames } from "../services/games";
import { fetchBounties } from "../services/bounties";
import type { Bounty } from "../services/bounties";
import type { Card, CardRarity } from "../types/card";
import type { Game } from "../types/game";

const router = useRouter();

const cards = ref<Card[]>([]);
const games = ref<Game[]>([]);
const bounties = ref<Bounty[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const showPicker = ref(false);
const pickerQuery = ref("");
const creating = ref(false);

const RARITY_LETTER: Record<CardRarity, string> = {
  common: "C",
  uncommon: "U",
  rare: "R",
  legendary: "L",
  mythic: "M",
};

const gameById = computed(() => new Map(games.value.map((g) => [g.id, g])));
const bountyById = computed(
  () => new Map(bounties.value.map((b) => [b.id, b])),
);
function isCardPrestiged(c: Card): boolean {
  return (
    !!c.bountyId && bountyById.value.get(c.bountyId)?.status === "completed"
  );
}

const eligibleGames = computed(() => {
  const cardedGameIds = new Set(cards.value.map((c) => c.gameId));
  return games.value.filter(
    (g) =>
      (g.status === "beaten" || g.status === "mastered") &&
      !cardedGameIds.has(g.id) &&
      g.title.toLowerCase().includes(pickerQuery.value.toLowerCase()),
  );
});

async function load() {
  loading.value = true;
  try {
    const [c, g, b] = await Promise.all([
      listCards(),
      fetchGames(),
      fetchBounties(),
    ]);
    cards.value = c;
    games.value = g;
    bounties.value = b;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load cards.";
  } finally {
    loading.value = false;
  }
}

async function handleCreate(gameId: string) {
  creating.value = true;
  try {
    const card = await createCard({ gameId });
    router.push(`/cards/${card.id}`);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to create card.";
  } finally {
    creating.value = false;
  }
}

onMounted(load);
</script>

<template>
  <main class="cards-page">
    <AccountChip fixed />
    <PageHeader
      title="Cards"
      description="Every Collector Card you've generated, front-face up."
    >
      <template #actions>
        <button
          type="button"
          class="ui-btn ui-btn-primary"
          @click="showPicker = true"
        >
          New card
        </button>
      </template>
    </PageHeader>

    <UiModal
      v-if="showPicker"
      title="New card"
      description="Choose a Beaten or Mastered game that doesn't already have a card."
      :dismissible="!creating"
      @close="showPicker = false"
    >
      <input
        v-model="pickerQuery"
        type="text"
        class="text-input"
        placeholder="Search Beaten/Mastered games…"
        aria-label="Search eligible games"
      />
      <p v-if="!eligibleGames.length" class="empty-state">
        No eligible games. A card can only be made for a game marked Beaten or
        Mastered that doesn't already have one.
      </p>
      <ul v-else class="picker-list">
        <li v-for="g in eligibleGames" :key="g.id" class="picker-item">
          <span>{{ g.title }}</span>
          <button
            type="button"
            class="secondary-button"
            :disabled="creating"
            @click="handleCreate(g.id)"
          >
            Create
          </button>
        </li>
      </ul>
    </UiModal>

    <p v-if="loading" class="empty-state">Loading…</p>
    <p v-else-if="error" class="empty-state error">{{ error }}</p>
    <p v-else-if="!cards.length" class="empty-state">No cards yet.</p>

    <div v-else class="cards-grid">
      <button
        v-for="c in cards"
        :key="c.id"
        type="button"
        class="card-tile"
        @click="router.push(`/cards/${c.id}`)"
      >
        <span v-if="c.rarity" class="rarity-chip">{{
          RARITY_LETTER[c.rarity]
        }}</span>
        <span v-if="isCardPrestiged(c)" class="prestige-chip">P</span>
        <span class="card-tile-title">{{
          gameById.get(c.gameId)?.title ?? "Unknown game"
        }}</span>
        <span class="card-tile-num"
          >#{{ String(c.archiveNumber ?? 0).padStart(3, "0") }}</span
        >
      </button>
    </div>
  </main>
</template>

<style scoped>
.cards-page {
  min-height: 100vh;
  background: var(--ui-bg);
  color: var(--ui-text);
  padding: 84px var(--ui-edge-right) 48px var(--ui-edge-left);
  box-sizing: border-box;
  font-family: var(--ui-font-family);
}
.empty-state {
  color: var(--ui-faint);
}
.empty-state.error {
  color: var(--ui-error);
}
.secondary-button {
  background: var(--ui-bg);
  border: 1px solid var(--ui-border);
  color: var(--ui-text);
  border-radius: var(--ui-radius-control);
  padding: 7px 12px;
  font-size: 0.8rem;
  cursor: pointer;
}
.secondary-button:disabled {
  opacity: 0.5;
  cursor: default;
}
.text-input {
  width: 100%;
  box-sizing: border-box;
  background: var(--ui-bg);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 9px 12px;
  font-size: 0.85rem;
  margin: 10px 0;
}
.picker-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.picker-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  gap: 12px;
}
.picker-item > span {
  min-width: 0;
  overflow-wrap: anywhere;
}
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(140px, 100%), 1fr));
  gap: 16px;
  margin-top: 20px;
}
.card-tile {
  position: relative;
  aspect-ratio: 5 / 7;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: flex-start;
  padding: 12px;
  cursor: pointer;
  color: var(--ui-text);
  text-align: left;
}
.card-tile:hover {
  border-color: var(--ui-accent);
}
.rarity-chip {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font-weight: 700;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.prestige-chip {
  position: absolute;
  top: 10px;
  left: 10px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1px solid var(--ui-accent);
  color: var(--ui-accent-text);
  font-weight: 700;
  font-size: 0.7rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-tile-title {
  font-weight: 600;
  font-size: 0.85rem;
}
.card-tile-num {
  font-size: 0.7rem;
  color: var(--ui-dim);
  margin-top: 4px;
}

.secondary-button,
.text-input {
  min-height: var(--ui-control-height);
  box-sizing: border-box;
}

@media (max-width: 760px) {
  .cards-page {
    padding-top: 84px;
  }
  .cards-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .card-tile-title {
    overflow-wrap: anywhere;
  }
}
</style>
