<script setup lang="ts">
// Games that may be in the library twice (added by hand, then brought in again by a
// Steam sync). Each pair can be merged, kept apart, or the decision changed later.
import { computed, onMounted, ref } from "vue";
import DuplicateReviewDialog from "../DuplicateReviewDialog.vue";
import {
  fetchMatches,
  reopenMatch,
  scanForMatches,
  type GameMatch,
} from "../../services/gameMatches";

const matches = ref<GameMatch[]>([]);
const loading = ref(true);
const scanning = ref(false);
const message = ref<string | null>(null);
const error = ref<string | null>(null);
const reviewing = ref<GameMatch | null>(null);

const pending = computed(() =>
  matches.value.filter((m) => m.status === "pending"),
);
const reviewed = computed(() =>
  matches.value.filter((m) => m.status !== "pending"),
);

async function load() {
  try {
    matches.value = (await fetchMatches()).items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not load this list.";
  } finally {
    loading.value = false;
  }
}

async function scan() {
  scanning.value = true;
  error.value = null;
  message.value = null;
  try {
    const found = await scanForMatches();
    message.value = found
      ? `Found ${found} new possible duplicate${found === 1 ? "" : "s"}.`
      : "No new possible duplicates.";
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "The search failed.";
  } finally {
    scanning.value = false;
  }
}

async function change(match: GameMatch) {
  error.value = null;
  try {
    await reopenMatch(match.id);
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not change that.";
  }
}

async function onResolved() {
  reviewing.value = null;
  await load();
}

onMounted(load);
</script>

<template>
  <section class="settings-section">
    <h2>Possible Duplicates</h2>
    <p class="section-hint">
      A game you added yourself can show up a second time when a Steam sync
      brings it in. Matches are found by title, and nothing is merged until you
      say so. You can change a decision at any time here, and a merge can be
      undone while the Steam copy is still in the trash.
    </p>

    <div class="tile">
      <div class="tile-head">
        <h3>
          To review
          <span v-if="pending.length" class="count">{{ pending.length }}</span>
        </h3>
        <button type="button" class="scan" :disabled="scanning" @click="scan">
          {{ scanning ? "Looking…" : "Look for duplicates" }}
        </button>
      </div>
      <p v-if="message" class="note">{{ message }}</p>
      <p v-if="error" class="form-error">{{ error }}</p>
      <p v-if="loading" class="note">Loading…</p>
      <p v-else-if="!pending.length" class="note">Nothing to review.</p>
      <ul v-else class="pairs">
        <li v-for="m in pending" :key="m.id">
          <div
            class="pair-cover"
            :style="{ backgroundImage: `url(${m.original.coverUrl})` }"
          ></div>
          <div class="pair-text">
            <span class="pair-title">{{ m.original.title }}</span>
            <span class="pair-sub"
              >Yours ({{ m.original.source ?? "added by hand" }}) and
              {{ m.steam.title }} from Steam</span
            >
          </div>
          <button type="button" class="review" @click="reviewing = m">
            Review
          </button>
        </li>
      </ul>
    </div>

    <div v-if="reviewed.length" class="tile">
      <h3>Reviewed</h3>
      <ul class="pairs">
        <li v-for="m in reviewed" :key="m.id">
          <div
            class="pair-cover"
            :style="{ backgroundImage: `url(${m.original.coverUrl})` }"
          ></div>
          <div class="pair-text">
            <span class="pair-title">{{ m.original.title }}</span>
            <span class="pair-sub">
              <span class="chip" :class="m.status">{{
                m.status === "merged"
                  ? `Merged, ${m.prefer === "steam" ? "Steam's" : "your"} details`
                  : "Kept both"
              }}</span>
            </span>
          </div>
          <button type="button" class="review" @click="change(m)">
            {{ m.status === "merged" ? "Undo merge" : "Ask again" }}
          </button>
        </li>
      </ul>
    </div>

    <DuplicateReviewDialog
      v-if="reviewing"
      :match="reviewing"
      @close="reviewing = null"
      @resolved="onResolved"
    />
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid #d68a34;
  font-size: 1rem;
  color: #fff;
}
.section-hint {
  margin: 0 0 20px;
  font-size: 0.82rem;
  line-height: 1.6;
  color: #999;
}
.tile {
  padding: 18px 20px;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  background: #111;
}
.tile + .tile {
  margin-top: 16px;
}
.tile h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 0.9rem;
  color: #fff;
}
.tile-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.count {
  min-width: 20px;
  padding: 1px 7px;
  border-radius: 999px;
  background: #d68a34;
  color: #0d0d0d;
  font-size: 0.72rem;
  font-weight: 800;
  text-align: center;
}
.note {
  margin: 0;
  font-size: 0.82rem;
  color: #999;
}
.form-error {
  margin: 8px 0 0;
  font-size: 0.82rem;
  color: #f87171;
}
.pairs {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}
.pairs li {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 12px;
  border: 1px solid #222;
  border-radius: 8px;
  background: #161616;
}
.pair-cover {
  flex: none;
  width: 40px;
  aspect-ratio: 2 / 3;
  border-radius: 4px;
  background: #222 center / cover no-repeat;
}
.pair-text {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.pair-title {
  overflow: hidden;
  font-size: 0.9rem;
  font-weight: 600;
  color: #fff;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pair-sub {
  font-size: 0.76rem;
  color: #8a8a8a;
}
.chip {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
}
.chip.merged {
  background: rgba(111, 191, 115, 0.16);
  color: #6fbf73;
}
.chip.kept_both {
  background: rgba(123, 167, 217, 0.16);
  color: #7ba7d9;
}
.review,
.scan {
  flex: none;
  padding: 7px 14px;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  background: transparent;
  color: #e5e5e5;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}
.review:hover,
.scan:hover:not(:disabled) {
  border-color: #d68a34;
  color: #d68a34;
}
.scan:disabled {
  opacity: 0.6;
  cursor: default;
}
.review:focus-visible,
.scan:focus-visible {
  outline: 2px solid #d68a34;
  outline-offset: 2px;
}
</style>
