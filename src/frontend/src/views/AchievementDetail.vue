<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchGame } from "../services/games";
import type { Achievement, Game } from "../types/game";

const route = useRoute();
const router = useRouter();

const game = ref<Game | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

const noteDraft = ref("");
const noteSaved = ref(false);

async function loadGame() {
  loading.value = true;
  error.value = null;
  try {
    game.value = await fetchGame(route.params.gameId as string);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load game";
  } finally {
    loading.value = false;
  }
}

const achievement = computed<Achievement | null>(() => {
  if (!game.value) return null;
  return (
    game.value.achievements.find((a) => a.id === route.params.achievementId) ??
    null
  );
});

watch(
  () => [route.params.gameId, route.params.achievementId],
  async () => {
    await loadGame();
    noteDraft.value = achievement.value?.notes ?? "";
  },
  { immediate: true },
);

function saveNote() {
  if (!achievement.value) return;
  achievement.value.notes = noteDraft.value;
  noteSaved.value = true;
  setTimeout(() => {
    noteSaved.value = false;
  }, 1500);
}

function onMediaFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file || !achievement.value) return;
  if (!achievement.value.media) achievement.value.media = [];
  achievement.value.media.push(URL.createObjectURL(file));
  (e.target as HTMLInputElement).value = "";
}

function removeMedia(index: number) {
  const url = achievement.value?.media?.[index];
  if (url) URL.revokeObjectURL(url);
  achievement.value?.media?.splice(index, 1);
}

function formatUnlockedAt(dateStr: string) {
  const d = new Date(dateStr);
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
}

function goBack() {
  router.push({ name: "game-detail", params: { id: route.params.gameId } });
}
</script>

<template>
  <main v-if="loading" class="achievement-detail loading-state">
    <p>Loading…</p>
  </main>

  <main v-else-if="error" class="achievement-detail error-state">
    <p>{{ error }}</p>
  </main>

  <main v-else-if="achievement" class="achievement-detail">
    <button type="button" class="back-button" @click="goBack">
      ← Back to {{ game?.title }}
    </button>

    <div class="achievement-header">
      <div
        class="achievement-icon-large"
        :style="{ backgroundImage: `url(${game?.coverImageUrl})` }"
      ></div>
      <div>
        <h1>{{ achievement.name }}</h1>
        <p v-if="achievement.description" class="achievement-desc">
          {{ achievement.description }}
        </p>
        <p v-if="achievement.unlockedAt" class="achievement-unlocked">
          Unlocked {{ formatUnlockedAt(achievement.unlockedAt) }}
        </p>
        <p v-else class="achievement-locked">Not yet unlocked</p>
      </div>
    </div>

    <section class="detail-section">
      <h2>Notes</h2>
      <textarea
        v-model="noteDraft"
        placeholder="Write notes about how you got this…"
        rows="6"
      ></textarea>
      <button type="button" class="primary-button" @click="saveNote">
        {{ noteSaved ? "Saved" : "Save note" }}
      </button>
    </section>

    <section class="detail-section">
      <h2>Media</h2>
      <input type="file" accept="image/*" @change="onMediaFileChange" />
      <div v-if="achievement.media?.length" class="media-grid">
        <div
          v-for="(url, i) in achievement.media"
          :key="url"
          class="media-item"
        >
          <img :src="url" alt="" />
          <button type="button" class="remove-button" @click="removeMedia(i)">
            ✕
          </button>
        </div>
      </div>
      <p v-else class="empty-state">No media added yet.</p>
    </section>
  </main>

  <main v-else class="not-found">
    <p>Achievement not found.</p>
  </main>
</template>

<style scoped>
.achievement-detail {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 24px;
  color: var(--ui-text);
  font-family: var(--ui-font-family);
  background: var(--ui-bg);
  min-height: 100vh;
  box-sizing: border-box;
}
.back-button {
  background: none;
  border: none;
  color: var(--ui-accent-text);
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  margin-bottom: 24px;
}
.achievement-header {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--ui-border);
  margin-bottom: 24px;
}
.achievement-icon-large {
  width: 96px;
  height: 96px;
  border-radius: 14px;
  background-size: cover;
  background-position: center;
  flex-shrink: 0;
}
.achievement-header h1 {
  margin: 0 0 8px;
  font-size: var(--ui-font-title);
}
.achievement-desc {
  color: var(--ui-text);
  margin: 0 0 8px;
}
.achievement-unlocked {
  color: var(--ui-accent-text);
  font-size: 13px;
  margin: 0;
}
.achievement-locked {
  color: var(--ui-faint);
  font-size: 13px;
  margin: 0;
}
.detail-section {
  margin-bottom: 32px;
}
.detail-section h2 {
  font-size: 1.1rem;
  margin: 0 0 12px;
}
.detail-section textarea {
  width: 100%;
  min-height: 140px;
  box-sizing: border-box;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-row);
  background: var(--ui-surface);
  color: var(--ui-text);
  resize: vertical;
  padding: 12px;
  font: inherit;
  margin-bottom: 10px;
}
.primary-button {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 10px 18px;
  font-weight: 600;
  cursor: pointer;
}
.media-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
}
.media-item {
  position: relative;
  width: 140px;
  height: 140px;
  border-radius: var(--ui-radius-row);
  overflow: hidden;
  border: 1px solid var(--ui-border);
}
.media-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.remove-button {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  border: none;
  border-radius: 50%;
  width: var(--ui-control-height);
  height: var(--ui-control-height);
  cursor: pointer;
}
.empty-state {
  color: var(--ui-faint);
  margin-top: 10px;
}
.not-found,
.loading-state,
.error-state {
  padding: 40px;
  color: var(--ui-text);
  text-align: center;
}
</style>
