<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  fetchGame,
  fetchGameAchievements,
  listGameNoteSummaries,
} from "../services/games";
import type { GameNoteSummary } from "../services/games";
import { isUnlocked } from "../utils/achievements";
import {
  listGameScreenshots,
  uploadGameScreenshots,
  updateMediaItem,
} from "../services/media";
import type { MediaItem } from "../services/media";
import {
  loadAchievementLocal,
  saveAchievementLocal,
} from "../state/achievementLocal";
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
    const id = route.params.gameId as string;
    const fetched = await fetchGame(id);
    // the game itself comes without its achievements, they're a separate call
    if (fetched) fetched.achievements = await fetchGameAchievements(id);
    game.value = fetched;
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
    noteDraft.value = achievement.value
      ? (loadAchievementLocal(route.params.gameId as string).notes[
          achievement.value.id
        ] ?? "")
      : "";
  },
  { immediate: true },
);

function saveNote() {
  if (!achievement.value) return;
  // kept on this device for now, the same place the Achievements tab keeps it
  const gameId = route.params.gameId as string;
  const local = loadAchievementLocal(gameId);
  const text = noteDraft.value.trim();
  if (text) local.notes[achievement.value.id] = text;
  else delete local.notes[achievement.value.id];
  saveAchievementLocal(gameId, local);
  achievement.value.notes = text;
  noteSaved.value = true;
  setTimeout(() => {
    noteSaved.value = false;
  }, 1500);
}

// Media here is the game's own uploads (the Screenshots, Clips and
// Soundtrack tabs) that are tied to this achievement. Adding one uploads it
// to the game and ties it to this achievement in one step.
// notes written about this achievement, from the game's Notes tab
const tiedNotes = ref<GameNoteSummary[]>([]);
async function loadTiedNotes() {
  try {
    const all = await listGameNoteSummaries(route.params.gameId as string);
    tiedNotes.value = all.filter(
      (n) => n.linked_achievement_id === route.params.achievementId,
    );
  } catch {
    tiedNotes.value = [];
  }
}
watch(() => route.params.achievementId, loadTiedNotes, { immediate: true });
function openNote(name: string) {
  void router.push({
    path: `/games/${route.params.gameId}`,
    query: { tab: "Notes", note: name },
  });
}

const linkedMedia = ref<MediaItem[]>([]);
const mediaError = ref<string | null>(null);
const mediaBusy = ref(false);
const lightbox = ref<string | null>(null);

async function loadLinkedMedia() {
  const gameId = route.params.gameId as string;
  const achievementId = route.params.achievementId as string;
  try {
    const all = await listGameScreenshots(gameId);
    linkedMedia.value = all.filter(
      (m) => m.linked_achievement_id === achievementId,
    );
  } catch (err) {
    mediaError.value =
      err instanceof Error ? err.message : "Failed to load media";
  }
}
watch(() => route.params.achievementId, loadLinkedMedia, { immediate: true });

async function onMediaFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = Array.from(input.files ?? []);
  input.value = "";
  if (!files.length || !achievement.value) return;
  const gameId = route.params.gameId as string;
  mediaBusy.value = true;
  mediaError.value = null;
  try {
    const results = await uploadGameScreenshots(gameId, files);
    const saved = new Set(
      results.filter((r) => r.status === "saved").map((r) => r.filename),
    );
    const rejected = results.filter((r) => r.status !== "saved");
    if (rejected.length) {
      mediaError.value = `${rejected[0].filename}: ${rejected[0].reason ?? "rejected"}`;
    }
    const all = await listGameScreenshots(gameId);
    for (const m of all.filter((m) => saved.has(m.filename))) {
      await updateMediaItem(gameId, m.id, {
        linked_achievement_id: achievement.value.id,
      });
    }
    await loadLinkedMedia();
  } catch (err) {
    mediaError.value = err instanceof Error ? err.message : "Upload failed";
  } finally {
    mediaBusy.value = false;
  }
}

async function unlinkMedia(item: MediaItem) {
  try {
    await updateMediaItem(route.params.gameId as string, item.id, {
      linked_achievement_id: null,
    });
    linkedMedia.value = linkedMedia.value.filter((m) => m.id !== item.id);
  } catch (err) {
    mediaError.value = err instanceof Error ? err.message : "Failed to remove";
  }
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
        :style="
          achievement.iconUrl
            ? { backgroundImage: `url(${achievement.iconUrl})` }
            : {}
        "
      ></div>
      <div>
        <h1>{{ achievement.name }}</h1>
        <p v-if="achievement.description" class="achievement-desc">
          {{ achievement.description }}
        </p>
        <p v-if="isUnlocked(achievement)" class="achievement-unlocked">
          Unlocked<template v-if="achievement.unlockedAt">
            {{ formatUnlockedAt(achievement.unlockedAt) }}</template
          >
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

    <section v-if="tiedNotes.length" class="detail-section">
      <h2>Notes about this</h2>
      <ul class="tied-notes">
        <li v-for="n in tiedNotes" :key="n.name">
          <button type="button" @click="openNote(n.name)">
            <strong>{{ n.name }}</strong>
            <span>{{
              n.preview
                .replace(/[#*_`>\-]/g, "")
                .trim()
                .slice(0, 140)
            }}</span>
          </button>
        </li>
      </ul>
    </section>

    <section class="detail-section">
      <h2>Media</h2>
      <label class="add-media">
        <input
          type="file"
          accept="image/*,video/*,audio/*"
          multiple
          :disabled="mediaBusy"
          @change="onMediaFileChange"
        />
        <span>{{ mediaBusy ? "Uploading…" : "+ Add media" }}</span>
      </label>
      <p v-if="mediaError" class="media-error">{{ mediaError }}</p>
      <div v-if="linkedMedia.length" class="media-grid">
        <div v-for="m in linkedMedia" :key="m.id" class="media-item">
          <img
            v-if="m.kind === 'screenshot'"
            :src="m.url"
            alt=""
            @click="lightbox = m.url"
          />
          <video v-else-if="m.kind === 'clip'" :src="m.url" controls></video>
          <audio v-else :src="m.url" controls></audio>
          <button
            type="button"
            class="remove-button"
            title="Untie from this achievement"
            @click="unlinkMedia(m)"
          >
            ✕
          </button>
        </div>
      </div>
      <p v-else class="empty-state">
        Nothing tied to this achievement yet. Add media here, or tie an existing
        screenshot or clip from its tab.
      </p>
    </section>
    <div v-if="lightbox" class="lightbox" @click="lightbox = null">
      <img :src="lightbox" alt="" />
    </div>
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
  border-radius: var(--ui-radius-dialog);
  background-size: cover;
  background-repeat: no-repeat;
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
  background: color-mix(in srgb, var(--ui-bg) 60%, transparent);
  color: var(--ui-text);
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
.add-media {
  display: inline-flex;
  align-items: center;
  height: 34px;
  padding: 0 16px;
  border-radius: var(--ui-radius-control);
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  align-self: flex-start;
}
.add-media input {
  display: none;
}
.media-error {
  color: var(--ui-error);
  font-size: 0.82rem;
  margin: 8px 0 0;
}
.media-item img {
  cursor: zoom-in;
}
.media-item video,
.media-item audio {
  width: 100%;
  display: block;
}
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: color-mix(in srgb, var(--ui-bg) 90%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  cursor: zoom-out;
}
.lightbox img {
  max-width: 100%;
  max-height: 100%;
  border-radius: var(--ui-radius-control);
}
.tied-notes {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tied-notes button {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  background: #161616;
  border: 1px solid var(--ui-surface-2);
  border-radius: var(--ui-radius-row);
  color: inherit;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.tied-notes button:hover {
  border-color: color-mix(in srgb, var(--ui-accent) 50%, transparent);
}
.tied-notes strong {
  font-size: 0.92rem;
  color: var(--ui-text);
}
.tied-notes span {
  font-size: 0.8rem;
  color: var(--ui-dim);
  overflow-wrap: anywhere;
}
</style>
