<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { fetchScanSettings, updateScanSettings } from "../../services/settings";
import type { DataProvider, ImageProvider } from "../../services/settings";
import ToggleButton from "./ToggleButton.vue";

const DATA_PROVIDER_LABELS: Record<DataProvider, string> = {
  Steam: "Steam",
  IGDB: "IGDB",
  GiantBomb: "Giant Bomb",
  GOG: "GOG",
  RetroAchievements: "RetroAchievements",
  HowLongToBeat: "HowLongToBeat (time to beat only)",
};
const IMAGE_PROVIDER_LABELS: Record<ImageProvider, string> = {
  SteamGridDB: "SteamGridDB",
  ScreenScraper: "ScreenScraper",
};

const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);
const saveSuccess = ref(false);

const providerOrder = ref<DataProvider[]>([
  "IGDB",
  "GiantBomb",
  "GOG",
  "Steam",
  "RetroAchievements",
  "HowLongToBeat",
]);
const imageProviderOrder = ref<ImageProvider[]>([
  "SteamGridDB",
  "ScreenScraper",
]);
const saveDeveloper = ref(true);
const savePublisher = ref(true);
const saveSeries = ref(true);
const saveTags = ref(true);
const saveFeatures = ref(true);
const saveDescription = ref(true);
const saveAgeRating = ref(true);
const saveReleaseDate = ref(true);
const saveTimeToBeat = ref(true);
const saveKeyArt = ref(true);
const saveBanner = ref(true);
const saveLogo = ref(true);
const saveIcon = ref(true);
const providerLastUsed = ref<Record<string, number>>({});

function lastUsedLabel(provider: string): string {
  const at = providerLastUsed.value[provider];
  if (!at) return "never used";
  const seconds = Date.now() / 1000 - at;
  if (seconds < 60) return "used just now";
  if (seconds < 3600) return `used ${Math.round(seconds / 60)}m ago`;
  if (seconds < 86400) return `used ${Math.round(seconds / 3600)}h ago`;
  return `used ${Math.round(seconds / 86400)}d ago`;
}

onMounted(async () => {
  try {
    const settings = await fetchScanSettings();
    providerOrder.value = settings.provider_order;
    imageProviderOrder.value = settings.image_provider_order;
    saveDeveloper.value = settings.save_developer;
    savePublisher.value = settings.save_publisher;
    saveSeries.value = settings.save_series;
    saveTags.value = settings.save_tags;
    saveFeatures.value = settings.save_features;
    saveDescription.value = settings.save_description;
    saveAgeRating.value = settings.save_age_rating;
    saveReleaseDate.value = settings.save_release_date;
    saveTimeToBeat.value = settings.save_time_to_beat;
    saveKeyArt.value = settings.save_key_art;
    saveBanner.value = settings.save_banner;
    saveLogo.value = settings.save_logo;
    saveIcon.value = settings.save_icon;
    providerLastUsed.value = settings.provider_last_used;
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to load scan settings";
  } finally {
    loading.value = false;
  }
});

// same as Profile/Appearance: without this, "Scan settings saved." keeps
// showing after a save even once the user starts changing something else,
// reading as if the new change was already saved
watch(
  [
    providerOrder,
    imageProviderOrder,
    saveDeveloper,
    savePublisher,
    saveSeries,
    saveTags,
    saveFeatures,
    saveDescription,
    saveAgeRating,
    saveReleaseDate,
    saveTimeToBeat,
    saveKeyArt,
    saveBanner,
    saveLogo,
    saveIcon,
  ],
  () => {
    saveSuccess.value = false;
  },
  { deep: true },
);

function reorder<T>(list: T[], index: number, direction: -1 | 1): T[] | null {
  const target = index + direction;
  if (target < 0 || target >= list.length) return null;
  const next = [...list];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

function moveDataProvider(index: number, direction: -1 | 1) {
  const next = reorder(providerOrder.value, index, direction);
  if (next) providerOrder.value = next;
}

function moveImageProvider(index: number, direction: -1 | 1) {
  const next = reorder(imageProviderOrder.value, index, direction);
  if (next) imageProviderOrder.value = next;
}

async function save() {
  saving.value = true;
  error.value = null;
  saveSuccess.value = false;
  try {
    await updateScanSettings({
      provider_order: providerOrder.value,
      image_provider_order: imageProviderOrder.value,
      save_developer: saveDeveloper.value,
      save_publisher: savePublisher.value,
      save_series: saveSeries.value,
      save_tags: saveTags.value,
      save_features: saveFeatures.value,
      save_description: saveDescription.value,
      save_age_rating: saveAgeRating.value,
      save_release_date: saveReleaseDate.value,
      save_time_to_beat: saveTimeToBeat.value,
      save_key_art: saveKeyArt.value,
      save_banner: saveBanner.value,
      save_logo: saveLogo.value,
      save_icon: saveIcon.value,
    });
    saveSuccess.value = true;
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to save scan settings";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Scan Settings</h2>
    <p class="section-hint">
      Controls how future metadata searches behave: which provider is checked
      first, and which fields a search result is allowed to save onto a game.
    </p>

    <p v-if="loading">Loading…</p>
    <template v-else>
      <div class="provider-order-row">
        <div class="field-block">
          <span class="field-label">Data provider order</span>
          <p class="field-sublabel">
            Which provider's text/data fields win when more than one has a
            match.
          </p>
          <ol class="provider-list">
            <li
              v-for="(provider, index) in providerOrder"
              :key="provider"
              class="provider-item"
            >
              <span class="provider-item-label">
                {{ DATA_PROVIDER_LABELS[provider] }}
                <small class="provider-last-used">{{
                  lastUsedLabel(provider)
                }}</small>
              </span>
              <div class="provider-arrows">
                <button
                  type="button"
                  :disabled="index === 0"
                  @click="moveDataProvider(index, -1)"
                >
                  ↑
                </button>
                <button
                  type="button"
                  :disabled="index === providerOrder.length - 1"
                  @click="moveDataProvider(index, 1)"
                >
                  ↓
                </button>
              </div>
            </li>
          </ol>
        </div>

        <div class="field-block">
          <span class="field-label">Image provider order</span>
          <p class="field-sublabel">
            Which provider's art wins when more than one has art.
          </p>
          <ol class="provider-list">
            <li
              v-for="(provider, index) in imageProviderOrder"
              :key="provider"
              class="provider-item"
            >
              <span class="provider-item-label">
                {{ IMAGE_PROVIDER_LABELS[provider] }}
                <small class="provider-last-used">{{
                  lastUsedLabel(provider)
                }}</small>
              </span>
              <div class="provider-arrows">
                <button
                  type="button"
                  :disabled="index === 0"
                  @click="moveImageProvider(index, -1)"
                >
                  ↑
                </button>
                <button
                  type="button"
                  :disabled="index === imageProviderOrder.length - 1"
                  @click="moveImageProvider(index, 1)"
                >
                  ↓
                </button>
              </div>
            </li>
          </ol>
        </div>
      </div>

      <div class="field-block">
        <span class="field-label">Images to save from a search result</span>
        <p class="field-sublabel">
          Turn an image type off to leave it untouched by search/refresh: useful
          if you keep your own art for something and don't want it overwritten.
        </p>
        <div class="refresh-options">
          <ToggleButton v-model="saveKeyArt" label="Key art">
            <strong>Key art</strong>: cover/box art, used as the game's poster
          </ToggleButton>
          <ToggleButton v-model="saveBanner" label="Banner">
            <strong>Banner</strong>: wide hero image for detail pages
          </ToggleButton>
          <ToggleButton v-model="saveLogo" label="Logo">
            <strong>Logo</strong>: transparent title logo
          </ToggleButton>
          <ToggleButton v-model="saveIcon" label="Icon">
            <strong>Icon</strong>: small square icon
          </ToggleButton>
        </div>
      </div>

      <div class="field-block">
        <span class="field-label">Data to save from a search result</span>
        <p class="field-sublabel">
          Turn a field off to leave it untouched by search/refresh: useful if
          you keep your own values for something and don't want them
          overwritten.
        </p>
        <div class="refresh-options">
          <ToggleButton v-model="saveDeveloper" label="Developer">
            <strong>Developer</strong>: the studio that made the game
          </ToggleButton>
          <ToggleButton v-model="savePublisher" label="Publisher">
            <strong>Publisher</strong>: who released it
          </ToggleButton>
          <ToggleButton v-model="saveSeries" label="Series">
            <strong>Series</strong>: franchise name, e.g. "Halo"
          </ToggleButton>
          <ToggleButton v-model="saveTags" label="Tags">
            <strong>Tags</strong>: Steam genre tags (RPG, Strategy, etc.)
          </ToggleButton>
          <ToggleButton v-model="saveFeatures" label="Features">
            <strong>Features</strong>: Steam categories (Co-op, Controller
            support, etc.)
          </ToggleButton>
          <ToggleButton v-model="saveDescription" label="Description">
            <strong>Description</strong>: the "About This Game" text and
            screenshots
          </ToggleButton>
          <ToggleButton v-model="saveAgeRating" label="Age rating">
            <strong>Age rating</strong>: e.g. "17+"
          </ToggleButton>
          <ToggleButton v-model="saveReleaseDate" label="Release date">
            <strong>Release date</strong>
          </ToggleButton>
          <ToggleButton v-model="saveTimeToBeat" label="Time to beat">
            <strong>Time to beat</strong>: main story hours, from HowLongToBeat
          </ToggleButton>
        </div>
      </div>

      <div v-if="error" class="form-error">{{ error }}</div>
      <div v-if="saveSuccess" class="form-success">Scan settings saved.</div>

      <button
        type="button"
        class="primary-button"
        :disabled="saving"
        @click="save"
      >
        {{ saving ? "Saving…" : "Save" }}
      </button>
    </template>
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
  color: #999;
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 16px;
}
.field-block {
  margin-bottom: 20px;
}
.provider-order-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 24px;
  margin-bottom: 20px;
}
.provider-order-row .field-block {
  margin-bottom: 0;
}
.field-label {
  display: block;
  font-size: 0.85rem;
  color: #ccc;
  margin-bottom: 4px;
}
.field-sublabel {
  color: #777;
  font-size: 0.76rem;
  line-height: 1.5;
  margin: 0 0 12px;
}
.provider-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.provider-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  padding: 10px 12px;
  color: #fff;
  font-size: 0.85rem;
}
.provider-item-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.provider-last-used {
  color: #777;
  font-size: 0.7rem;
  font-weight: 400;
}
.provider-arrows {
  display: flex;
  gap: 4px;
}
.provider-arrows button {
  background: rgba(255, 255, 255, 0.08);
  border: none;
  border-radius: 6px;
  color: #fff;
  width: 26px;
  height: 26px;
  cursor: pointer;
}
.provider-arrows button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.refresh-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.form-error {
  color: #fca5a5;
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 14px;
}
.form-success {
  color: #86efac;
  font-size: 13px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 14px;
}
.primary-button {
  background: #d68a34;
  color: #111;
  border: none;
  border-radius: 8px;
  padding: 11px 20px;
  font-weight: 600;
  cursor: pointer;
}
.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
