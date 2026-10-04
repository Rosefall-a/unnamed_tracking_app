<script setup lang="ts">
import PageHeader from "../components/PageHeader.vue";
import AccountChip from "../components/AccountChip.vue";
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { fetchSets, createSet } from "../services/set";
import type { CardSet } from "../types/set";

const router = useRouter();

const sets = ref<CardSet[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const newName = ref("");
const newTarget = ref<number | null>(null);
const creating = ref(false);
const createError = ref<string | null>(null);

async function load() {
  loading.value = true;
  try {
    sets.value = await fetchSets();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load sets.";
  } finally {
    loading.value = false;
  }
}

async function handleCreate() {
  if (creating.value) return;
  const name = newName.value.trim();
  if (!name) return;
  creating.value = true;
  createError.value = null;
  try {
    await createSet({ name, targetTotal: newTarget.value });
    newName.value = "";
    newTarget.value = null;
    await load();
  } catch (e) {
    createError.value =
      e instanceof Error ? e.message : "Failed to create set.";
  } finally {
    creating.value = false;
  }
}

onMounted(load);
</script>

<template>
  <main class="sets-page">
    <AccountChip fixed />
    <PageHeader
      title="Sets"
      description="Group cards with a position and total. Assign a card to a set from the card's detail page. When every expected card is in, the set shows as complete."
    />

    <form class="create-row" @submit.prevent="handleCreate">
      <input
        v-model="newName"
        type="text"
        class="text-input"
        placeholder="New set name"
        aria-label="New set name"
      />
      <input
        v-model.number="newTarget"
        type="number"
        min="1"
        class="text-input target-input"
        placeholder="Total (optional)"
        aria-label="Expected card total (optional)"
      />
      <button
        type="submit"
        class="add-button"
        :disabled="creating || !newName.trim()"
      >
        + Create Set
      </button>
    </form>
    <p v-if="createError" class="error">{{ createError }}</p>

    <p v-if="loading" class="empty-state">Loading…</p>
    <p v-else-if="error" class="empty-state error">{{ error }}</p>
    <p v-else-if="!sets.length" class="empty-state">No sets yet.</p>

    <div v-else class="sets-grid">
      <button
        v-for="s in sets"
        :key="s.id"
        type="button"
        class="set-card"
        :class="{ complete: s.isComplete }"
        @click="router.push(`/sets/${s.id}`)"
      >
        <span v-if="s.isComplete" class="complete-badge">COMPLETE</span>
        <h3>{{ s.name }}</h3>
        <p class="progress">
          {{
            s.targetTotal
              ? `${s.cardCount} / ${s.targetTotal}`
              : `${s.cardCount} card${s.cardCount === 1 ? "" : "s"}`
          }}
        </p>
      </button>
    </div>
  </main>
</template>

<style scoped>
.sets-page {
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
.empty-state.error,
.error {
  color: var(--ui-error);
}
.add-button {
  background: var(--ui-accent);
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 9px 14px;
  font-size: 0.85rem;
  color: var(--ui-on-accent);
  font-weight: 700;
  cursor: pointer;
}
.add-button:disabled {
  opacity: 0.5;
  cursor: default;
}
.create-row {
  display: flex;
  gap: 10px;
  margin: 18px 0;
  flex-wrap: wrap;
}
.text-input {
  min-width: 0;
  max-width: 100%;
  flex: 1 1 220px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 9px 12px;
  font-size: 0.85rem;
}
.target-input {
  width: 160px;
  flex: 0 1 160px;
}
.sets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(220px, 100%), 1fr));
  gap: 16px;
  margin-top: 20px;
}
.set-card {
  position: relative;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  padding: 18px;
  text-align: left;
  cursor: pointer;
  color: var(--ui-text);
}
.set-card:hover {
  border-color: var(--ui-accent);
}
.set-card.complete {
  border-color: var(--ui-accent);
}
.complete-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  font-size: 0.6rem;
  font-weight: 700;
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  border-radius: 999px;
  padding: 2px 8px;
}
.set-card h3 {
  margin: 0 0 6px;
  font-size: 1rem;
}
.progress {
  color: var(--ui-dim);
  font-size: 0.85rem;
  margin: 0;
}

.add-button,
.text-input {
  min-height: var(--ui-control-height);
  box-sizing: border-box;
}

@media (max-width: 760px) {
  .sets-page {
    padding-top: 84px;
  }
}
</style>
