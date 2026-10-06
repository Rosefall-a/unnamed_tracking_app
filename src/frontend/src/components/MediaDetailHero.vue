<script setup lang="ts">
// The banner at the top of a Movie, TV show or Anime page: backdrop, poster,
// title, status and rating pickers, a few badges, and the Edit / favorite /
// extras buttons. What goes in it (which badges, the movie's "Left off at"
// row, an anime's other titles) is the page's call, through props and slots.
import { STATUS_BUCKETS } from "../utils/mediaStatus";
import MediaExtrasPanel from "./MediaExtrasPanel.vue";
import RatingPicker from "./RatingPicker.vue";

defineProps<{
  title: string;
  // the line above the title, like "Movie · Christopher Nolan"
  nativeTitle: string;
  posterUrl: string | null;
  // the picture behind the hero; null when there is none at all
  heroBackdropUrl: string | null;
  // false when that picture is really the poster, which is shown differently
  hasBackdrop: boolean;
  ratingOverall: number | null;
  favorite: boolean;
  mediaType: "movie" | "tv" | "anime";
  mediaId: string;
  badges: { text: string; tone?: "good" }[];
  // the native-title line is lighter on Anime pages
  brightNativeTitle?: boolean;
}>();

const status = defineModel<string>("status", { required: true });

const emit = defineEmits<{
  "status-change": [];
  "rating-change": [value: number | null];
  edit: [];
  "toggle-favorite": [];
}>();
</script>

<template>
  <section class="hero" :class="{ 'no-poster': !heroBackdropUrl }">
    <div
      v-if="heroBackdropUrl"
      class="hero-backdrop"
      :class="{ 'is-poster': !hasBackdrop }"
      :style="{ backgroundImage: `url(${heroBackdropUrl})` }"
    ></div>
    <div class="hero-overlay"></div>
    <div class="hero-content">
      <div
        class="poster-card"
        :style="posterUrl ? { backgroundImage: `url(${posterUrl})` } : {}"
      >
        <span v-if="!posterUrl">{{ title }}</span>
      </div>
      <div class="hero-text">
        <div class="native-title" :class="{ bright: brightNativeTitle }">
          {{ nativeTitle }}
        </div>
        <h1 class="title">{{ title }}</h1>
        <slot name="subtitle" />
        <div class="badge-row">
          <select
            v-model="status"
            class="badge status status-select"
            title="Change status"
            @change="emit('status-change')"
          >
            <option
              v-for="opt in STATUS_BUCKETS"
              :key="opt.key"
              :value="opt.key"
            >
              {{ opt.label }}
            </option>
          </select>
          <RatingPicker
            :model-value="ratingOverall"
            @change="emit('rating-change', $event)"
          />
          <span
            v-for="badge in badges"
            :key="badge.text"
            class="badge"
            :class="badge.tone"
            >{{ badge.text }}</span
          >
        </div>
        <slot name="below-badges" />
        <div class="action-row">
          <button class="edit-btn" type="button" @click="emit('edit')">
            ✎ Edit
          </button>
          <button
            class="icon-btn"
            :class="{ active: favorite }"
            type="button"
            :title="favorite ? 'Remove from favorites' : 'Add to favorites'"
            @click="emit('toggle-favorite')"
          >
            <svg
              viewBox="0 0 24 24"
              width="16"
              height="16"
              :fill="favorite ? 'currentColor' : 'none'"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path
                d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.6z"
              />
            </svg>
          </button>
          <MediaExtrasPanel :media-type="mediaType" :media-id="mediaId" />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero-backdrop {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center 20%;
  filter: brightness(0.55) saturate(1.15);
  z-index: 0;
}

.hero-backdrop.is-poster {
  inset: -30px;
  filter: blur(18px) brightness(0.55) saturate(1.15);
  transform: translateZ(0);
}

.hero-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
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
  z-index: 2;
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 24px 28px;
  display: flex;
  align-items: flex-end;
  gap: 26px;
}

.hero-text {
  min-width: 0;
  padding-bottom: 4px;
}

.hero {
  position: relative;
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center 25%;
  background-color: #1a1a1a;
  min-height: 440px;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}

.hero.no-poster {
  background: linear-gradient(160deg, #241a10, #0d0d0d 70%);
}

.poster-card {
  width: 190px;
  aspect-ratio: 2 / 3;
  flex-shrink: 0;
  border-radius: 8px;
  background-size: cover;
  background-repeat: no-repeat;
  background-origin: border-box;
  background-clip: border-box;
  background-position: center;
  background-color: #222222;
  border: 1px solid transparent;
  box-shadow: 0 24px 48px -14px rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.3);
  text-align: center;
  padding: 10px;
}

.title {
  font-weight: 800;
  font-size: 2.5rem;
  line-height: 1.05;
  margin: 0 0 14px;
  letter-spacing: -0.01em;
  text-shadow: 0 4px 24px rgba(0, 0, 0, 0.5);
}

.badge-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.badge {
  line-height: 1.25;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 7px;
  padding: 4px 11px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #9c9c9c;
  text-transform: capitalize;
}

.status-select option {
  background: #171717;
  color: #f2f2f2;
}

.status-select {
  color-scheme: dark;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  border-color: rgba(214, 138, 52, 0.4);
  color: #d68a34;
  font-family: inherit;
  cursor: pointer;
  padding-right: 26px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d68a34' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 10px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.edit-btn {
  background: #d68a34;
  border: none;
  color: #14100a;
  border-radius: 8px;
  padding: 0 20px;
  height: 38px;
  font-family: inherit;
  font-size: 0.86rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}

.icon-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #f2f2f2;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.icon-btn:hover {
  border-color: rgba(214, 138, 52, 0.4);
}

.icon-btn.active {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.4);
  background: rgba(214, 138, 52, 0.16);
}

@media (max-width: 640px) {
  .hero-content {
    flex-direction: column;
    align-items: flex-start;
  }
}
.native-title {
  font-size: 0.82rem;
  color: #666;
  margin-bottom: 4px;
  font-weight: 500;
}

.native-title.bright {
  color: #9a9a9a;
}

.badge.good {
  background: rgba(111, 191, 115, 0.16);
  border-color: rgba(111, 191, 115, 0.4);
  color: #6fbf73;
}
</style>
