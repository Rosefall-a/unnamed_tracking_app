<script setup lang="ts">
// Covers and banners to choose from while adding a game, fetched live from
// SteamGridDB. What the search list showed stays the cover until one is picked.
import { onMounted, ref } from "vue";
import { fetchArtOptions } from "../services/games";
import ArtStrip from "./ArtStrip.vue";

const props = defineProps<{
  title: string;
  provider: string;
  providerId: string;
  // the cover already chosen by the search list, shown as the starting pick
  currentCover: string | null;
  // what the cover already in place is called ("Search" when adding)
  currentLabel?: string;
}>();
const cover = defineModel<string | null>("cover", { required: true });
const banner = defineModel<string | null>("banner", { required: true });

const covers = ref<string[]>([]);
const banners = ref<string[]>([]);
const loading = ref(true);
const note = ref<string | null>(null);

// SteamGridDB keeps a small JPEG of every grid beside the full PNG
function thumb(url: string): string {
  return url.replace("/grid/", "/thumb/").replace(/\.\w+$/, ".jpg");
}

onMounted(async () => {
  // a different game starts from its own listed cover
  cover.value = null;
  banner.value = null;
  try {
    const found = await fetchArtOptions(
      props.title,
      props.provider,
      props.providerId,
    );
    covers.value = found.covers;
    banners.value = found.banners;
    if (!found.configured) {
      note.value = "Add a SteamGridDB key in Settings to pick other artwork.";
    } else if (!found.covers.length && !found.banners.length) {
      note.value = "No other artwork found for this game.";
    }
  } catch {
    note.value = "Could not load other artwork.";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="art-picker">
    <p class="art-label">
      Cover
      <span v-if="loading" class="art-status">loading options…</span>
    </p>
    <ArtStrip>
      <button
        v-if="currentCover"
        type="button"
        class="art-tile cover"
        :class="{ chosen: cover === null }"
        :title="
          currentLabel
            ? 'The cover that is in place now'
            : 'The cover from the search'
        "
        @click="cover = null"
      >
        <img :src="currentCover" alt="Cover from the search" />
        <span v-if="cover === null" class="art-check">&#10003;</span>
        <span class="art-tag">{{ currentLabel ?? "Search" }}</span>
      </button>
      <button
        v-for="url in covers"
        :key="url"
        type="button"
        class="art-tile cover"
        :class="{ chosen: cover === url }"
        @click="cover = url"
      >
        <img :src="thumb(url)" alt="Cover option" loading="lazy" />
        <span v-if="cover === url" class="art-check">&#10003;</span>
      </button>
    </ArtStrip>

    <template v-if="banners.length">
      <p class="art-label">Banner</p>
      <ArtStrip>
        <button
          v-for="url in banners"
          :key="url"
          type="button"
          class="art-tile banner"
          :class="{ chosen: banner === url }"
          @click="banner = banner === url ? null : url"
        >
          <img :src="url" alt="Banner option" loading="lazy" />
          <span v-if="banner === url" class="art-check">&#10003;</span>
        </button>
      </ArtStrip>
    </template>
    <p v-if="note" class="art-status">{{ note }}</p>
  </div>
</template>

<style scoped>
.art-picker {
  grid-column: 1 / -1;
  min-width: 0;
}
.art-label {
  margin: 6px 0;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ui-dim-2);
}
.art-status {
  margin-left: 6px;
  font-size: 0.75rem;
  font-weight: 400;
  letter-spacing: 0;
  text-transform: none;
  color: var(--ui-dim-2);
}
.art-tile {
  position: relative;
  flex: none;
  scroll-snap-align: start;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 8px;
  background: var(--ui-surface-2);
  overflow: hidden;
  cursor: pointer;
  transition:
    transform 0.12s ease,
    border-color 0.12s ease;
}
.art-tile img {
  display: block;
  height: 100%;
  width: 100%;
  object-fit: cover;
}
.art-tile.cover {
  width: 124px;
  height: 186px;
}
.art-tile.banner {
  width: 280px;
  height: 90px;
}
.art-tile:hover {
  transform: translateY(-2px);
  border-color: var(--ui-border-hover);
}
.art-tile.chosen {
  border-color: var(--ui-accent);
}
.art-tile:focus-visible {
  outline: 2px solid var(--ui-accent);
  outline-offset: 2px;
}
.art-check {
  position: absolute;
  top: 6px;
  right: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--ui-accent);
  color: var(--ui-bg);
  font-size: 0.8rem;
  font-weight: 800;
}
.art-tag {
  position: absolute;
  left: 6px;
  bottom: 6px;
  padding: 1px 6px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--ui-bg) 80%, transparent);
  color: #cfcfcf;
  font-size: 0.65rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
</style>
