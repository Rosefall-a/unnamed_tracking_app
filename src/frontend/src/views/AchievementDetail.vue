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
  deleteGameScreenshot,
  listGameScreenshots,
  uploadGameScreenshots,
  updateMediaItem,
} from "../services/media";
import type { MediaItem, MediaItemUpdate } from "../services/media";
import GameNoteCard from "../components/GameNoteCard.vue";
import MediaTile from "../components/MediaTile.vue";
import {
  copyImage,
  copyLink,
  downloadMedia,
  originalName,
} from "../utils/copyMedia";
import {
  loadAchievementLocal,
  saveAchievementLocal,
} from "../state/achievementLocal";
import type { Achievement, Game } from "../types/game";
import { HERO_WIDTH, sizedAssetUrl } from "../utils/gameImages";
import BackButton from "../components/BackButton.vue";
import GameTopBar from "../components/GameTopBar.vue";

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
const lightbox = ref<MediaItem | null>(null);

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

// The same actions as the game's Screenshots tab: edit (which includes
// un-tying it from this achievement), delete (to Deleted), copy and download.
async function saveMedia(item: MediaItem, patch: MediaItemUpdate) {
  try {
    await updateMediaItem(route.params.gameId as string, item.id, patch);
    await loadLinkedMedia();
  } catch (err) {
    mediaError.value = err instanceof Error ? err.message : "Failed to save";
  }
}
async function deleteMedia(item: MediaItem) {
  try {
    await deleteGameScreenshot(
      route.params.gameId as string,
      item.kind,
      item.filename,
    );
    await loadLinkedMedia();
  } catch (err) {
    mediaError.value = err instanceof Error ? err.message : "Failed to delete";
  }
}
async function copyMedia(item: MediaItem) {
  try {
    if (item.kind === "screenshot") await copyImage(item.url);
    else await copyLink(item.url);
  } catch {
    mediaError.value = "Could not copy. Your browser blocked clipboard access.";
  }
}
function downloadItem(item: MediaItem) {
  downloadMedia(item.url, originalName(item.filename));
}

function formatUnlockedAt(dateStr: string) {
  const d = new Date(dateStr);
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
}

const unlocked = computed(
  () => !!achievement.value && isUnlocked(achievement.value),
);
// the larger copy the server makes of the (small) provider icon
const iconSrc = computed(() => {
  const url = achievement.value?.iconUrl;
  if (!url) return null;
  return url.startsWith("/api/achievement-icon/") ? `${url}?large=1` : url;
});
const heroStyle = computed(() =>
  game.value?.bannerImageUrl
    ? {
        backgroundImage: `url(${sizedAssetUrl(game.value.bannerImageUrl, HERO_WIDTH)})`,
      }
    : {},
);

// Going back means back in history. Pushing the game page again would add a
// new entry each time, and the game page's own back would return here: a loop.
function goBack() {
  if (router.options.history.state.back) router.back();
  else
    void router.push({
      name: "game-detail",
      params: { id: route.params.gameId },
    });
}
</script>

<template>
  <main v-if="loading" class="detail loading-state">
    <GameTopBar active="games" />
    <p class="loading-text">Loading…</p>
  </main>

  <main v-else-if="error" class="detail error-state">
    <GameTopBar active="games" />
    <p class="loading-text">{{ error }}</p>
  </main>

  <main v-else-if="achievement && game" class="detail">
    <GameTopBar active="games" />
    <BackButton class="back-spot" @click="goBack" />

    <section class="hero">
      <div class="hero-backdrop" :style="heroStyle"></div>
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <div
          class="icon-card"
          :style="iconSrc ? { backgroundImage: `url(${iconSrc})` } : {}"
        ></div>
        <div class="hero-text">
          <router-link :to="`/games/${game.id}`" class="game-link">{{
            game.title
          }}</router-link>
          <h1 class="title">{{ achievement.name }}</h1>
          <p v-if="achievement.description" class="desc">
            {{ achievement.description }}
          </p>
          <div class="chip-row">
            <span class="chip" :class="{ primary: unlocked }">{{
              unlocked ? "Unlocked" : "Locked"
            }}</span>
            <span v-if="achievement.hidden" class="chip">Hidden</span>
            <span v-if="achievement.provider" class="chip">{{
              achievement.provider
            }}</span>
          </div>
        </div>
      </div>
    </section>

    <div class="body">
      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">Status</span>
          <span class="meta-value" :class="{ accent: unlocked }">
            {{ unlocked ? "Unlocked" : "Not yet unlocked" }}
            <template v-if="unlocked && achievement.unlockedAt">
              {{ formatUnlockedAt(achievement.unlockedAt) }}</template
            >
          </span>
        </div>
        <div v-if="achievement.rarityPercent != null" class="meta-item">
          <span class="meta-label">Rarity</span>
          <span class="meta-value"
            >{{ achievement.rarityPercent }}% of players</span
          >
        </div>
        <div v-if="achievement.progressTarget" class="meta-item">
          <span class="meta-label">Progress</span>
          <span class="meta-value"
            >{{ achievement.progressCurrent ?? 0 }} /
            {{ achievement.progressTarget }}</span
          >
        </div>
      </div>

      <section class="block">
        <div class="section-heading"><h2>Notes</h2></div>
        <textarea
          v-model="noteDraft"
          class="ui-field note-field"
          placeholder="Write notes about how you got this…"
          rows="6"
        ></textarea>
        <button
          type="button"
          class="ui-btn ui-btn-primary ui-btn-sm"
          @click="saveNote"
        >
          {{ noteSaved ? "Saved" : "Save note" }}
        </button>
      </section>

      <section v-if="tiedNotes.length" class="block">
        <div class="section-heading"><h2>Notes about this</h2></div>
        <div class="card-grid notes-grid">
          <GameNoteCard
            v-for="n in tiedNotes"
            :key="n.name"
            :note="n"
            :achievement-name="achievement.name"
            @open="openNote(n.name)"
          />
        </div>
      </section>

      <section class="block">
        <div class="section-heading">
          <h2>Media</h2>
          <label class="ui-btn ui-btn-primary ui-btn-sm">
            <input
              type="file"
              accept="image/*,video/*,audio/*"
              multiple
              hidden
              :disabled="mediaBusy"
              @change="onMediaFileChange"
            />
            {{ mediaBusy ? "Uploading…" : "+ Add media" }}
          </label>
        </div>
        <p v-if="mediaError" class="ui-error-box">{{ mediaError }}</p>
        <div v-if="linkedMedia.length" class="card-grid media-grid">
          <MediaTile
            v-for="m in linkedMedia"
            :key="m.id"
            :item="m"
            :achievements="game.achievements"
            @preview="lightbox = $event"
            @save="saveMedia"
            @delete="deleteMedia"
            @copy="copyMedia"
            @download="downloadItem"
          />
        </div>
        <p v-else class="empty-state">
          Nothing tied to this achievement yet. Add media here, or tie an
          existing screenshot or clip from its tab.
        </p>
      </section>
    </div>
    <div v-if="lightbox" class="lightbox" @click="lightbox = null">
      <img v-if="lightbox.kind === 'screenshot'" :src="lightbox.url" alt="" />
      <video v-else :src="lightbox.url" controls autoplay @click.stop></video>
    </div>
  </main>

  <main v-else class="detail loading-state">
    <GameTopBar active="games" />
    <p class="loading-text">Achievement not found.</p>
  </main>
</template>

<style scoped src="../styles/shared/mediaDetail.css"></style>
<style scoped>
/* the hero is the Game page's, with a smaller icon card in place of the poster */
.hero {
  position: relative;
  background-color: #1a1a1a;
  min-height: 300px;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}
.hero-backdrop {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center 20%;
  filter: brightness(0.55) saturate(1.15);
}
.hero-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(
      180deg,
      rgba(13, 13, 13, 0.25) 0%,
      rgba(13, 13, 13, 0.55) 45%,
      #0d0d0d 96%
    ),
    linear-gradient(
      90deg,
      rgba(13, 13, 13, 0.75) 0%,
      rgba(13, 13, 13, 0.15) 40%
    );
}
.hero-content {
  position: relative;
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 24px 28px;
  box-sizing: border-box;
  display: flex;
  align-items: flex-end;
  gap: 26px;
}
.icon-card {
  width: 120px;
  height: 120px;
  flex-shrink: 0;
  border-radius: 14px;
  background: #222222 center / cover no-repeat;
  box-shadow: 0 24px 48px -14px rgba(0, 0, 0, 0.8);
}
.hero-text {
  min-width: 0;
}
.game-link {
  color: #9c9c9c;
  font-size: 0.85rem;
  font-weight: 600;
  text-decoration: none;
}
.game-link:hover {
  color: #fff;
}
.title {
  font-weight: 800;
  font-size: 2.2rem;
  line-height: 1.05;
  margin: 4px 0 10px;
  letter-spacing: -0.01em;
  text-shadow: 0 4px 24px rgba(0, 0, 0, 0.5);
}
.desc {
  color: #ccc;
  margin: 0 0 12px;
  max-width: 640px;
}
.block {
  margin-bottom: 32px;
}
.note-field {
  width: 100%;
  margin-bottom: 10px;
}
.card-grid {
  display: grid;
  gap: 16px;
}
.notes-grid {
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
}
.media-grid {
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}
.lightbox {
  position: fixed;
  inset: 0;
  z-index: var(--ui-z-modal);
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  cursor: zoom-out;
}
.lightbox img,
.lightbox video {
  max-width: 100%;
  max-height: 100%;
  border-radius: 8px;
}
@media (max-width: 640px) {
  .hero-content {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
