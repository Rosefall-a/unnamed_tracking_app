<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import SegmentedControl from "./SegmentedControl.vue";
import {
  fetchAppearanceSettings,
  updateAppearanceSettings,
  uploadBadgeImage,
  deleteBadgeImage,
} from "../../services/appearanceSettings";
import type {
  BadgeStyle,
  BadgePlacement,
} from "../../services/appearanceSettings";
import { loadAppearanceSettings } from "../../state/appearance";
import UiAppearanceSection from "./UiAppearanceSection.vue";
import CompletionBadge from "../CompletionBadge.vue";

const previewTitles = [
  "Inventory Full Again",
  "Side Quest: Laundry",
  "Oops, All Side Quests",
  "The Final Final Boss",
  "Save Point Simulator",
  "One More Turn, Honest",
  "Loot Goblin Academy",
  "Achievement: Went Outside",
];
const previewTitle =
  previewTitles[Math.floor(Math.random() * previewTitles.length)]!;
const previewCoverUrl = `/api/game/preview-cover?title=${encodeURIComponent(previewTitle)}`;

const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);
const saveSuccess = ref(false);

const style = ref<BadgeStyle>("glow");
const color = ref("#e5e4e2");
const placement = ref<BadgePlacement>("top-right");
const imageUrl = ref<string | null>(null);

const styleOptions = [
  { value: "none", label: "Off" },
  { value: "glow", label: "Glow" },
  { value: "border", label: "Border" },
  { value: "ribbon", label: "Ribbon" },
  { value: "corner_badge", label: "Corner badge" },
];
const placementOptions = [
  { value: "top-left", label: "Top left" },
  { value: "top-right", label: "Top right" },
  { value: "bottom-left", label: "Bottom left" },
  { value: "bottom-right", label: "Bottom right" },
];

const usesPlacement = computed(
  () => style.value === "ribbon" || style.value === "corner_badge",
);
const usesImage = computed(
  () => style.value === "ribbon" || style.value === "corner_badge",
);

onMounted(async () => {
  try {
    const settings = await fetchAppearanceSettings();
    style.value = settings.completion_badge_style;
    color.value = settings.completion_badge_color;
    placement.value = settings.completion_badge_placement;
    imageUrl.value = settings.completion_badge_image_url;
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to load appearance settings";
  } finally {
    loading.value = false;
  }
});

async function save() {
  saving.value = true;
  error.value = null;
  saveSuccess.value = false;
  try {
    await updateAppearanceSettings({
      completion_badge_style: style.value,
      completion_badge_color: color.value,
      completion_badge_placement: placement.value,
    });
    await loadAppearanceSettings();
    saveSuccess.value = true;
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to save appearance settings";
  } finally {
    saving.value = false;
  }
}

watch([style, color, placement], () => {
  saveSuccess.value = false;
});

const uploading = ref(false);
async function onImageSelected(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  uploading.value = true;
  error.value = null;
  try {
    const settings = await uploadBadgeImage(file);
    imageUrl.value = settings.completion_badge_image_url;
    await loadAppearanceSettings();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to upload badge image";
  } finally {
    uploading.value = false;
    input.value = "";
  }
}

async function removeImage() {
  uploading.value = true;
  error.value = null;
  try {
    await deleteBadgeImage();
    imageUrl.value = null;
    await loadAppearanceSettings();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to remove badge image";
  } finally {
    uploading.value = false;
  }
}
</script>

<template>
  <UiAppearanceSection />
  <section class="settings-section">
    <h2>Completed game badges</h2>
    <p class="section-hint">
      How a 100%-complete (Mastered) game's card is highlighted in your library.
      Your saved badges follow your account. Other people's badges are
      unaffected.
    </p>

    <p v-if="loading">Loading…</p>
    <template v-else>
      <div class="field">
        <span>Badge style</span>
        <SegmentedControl
          :model-value="style"
          :options="styleOptions"
          @update:model-value="style = $event as BadgeStyle"
        />
      </div>

      <div v-if="style !== 'none'" class="field">
        <span>Color</span>
        <div class="color-row">
          <input
            v-model="color"
            type="color"
            class="color-input"
            aria-label="Badge color"
          />
          <input
            v-model="color"
            type="text"
            class="color-text"
            aria-label="Badge hex color"
            maxlength="7"
          />
        </div>
      </div>

      <div v-if="usesPlacement" class="field">
        <span>Placement</span>
        <SegmentedControl
          :model-value="placement"
          :options="placementOptions"
          @update:model-value="placement = $event as BadgePlacement"
        />
      </div>

      <div v-if="usesImage" class="field">
        <span>Custom badge image</span>
        <p class="field-sublabel">
          Optional: replaces the default trophy icon. A small square/round image
          works best.
        </p>
        <div class="image-row">
          <div
            class="image-preview"
            :style="imageUrl ? { backgroundImage: `url(${imageUrl})` } : {}"
          >
            <svg
              v-if="!imageUrl"
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="currentColor"
            >
              <path
                d="M12 2l2.4 6.6L21 9l-5 4.6L17.4 21 12 17.3 6.6 21 8 13.6 3 9l6.6-.4z"
              />
            </svg>
          </div>
          <label class="secondary-button upload-label">
            {{ uploading ? "Uploading…" : "Upload image" }}
            <input
              type="file"
              accept="image/*"
              class="hidden-input"
              :disabled="uploading"
              @change="onImageSelected"
            />
          </label>
          <button
            v-if="imageUrl"
            type="button"
            class="secondary-button"
            :disabled="uploading"
            @click="removeImage"
          >
            Remove
          </button>
        </div>
      </div>

      <div v-if="style !== 'none'" class="field">
        <span>Preview</span>
        <div class="preview-row">
          <div
            class="preview-card"
            :class="[`badge-${style}`]"
            :style="{ '--badge-color': color }"
          >
            <div class="preview-cover">
              <img
                class="preview-art"
                :src="previewCoverUrl"
                :alt="`${previewTitle} default game cover`"
              />
              <CompletionBadge
                v-if="usesPlacement"
                :badge-style="style"
                :placement="placement"
                :color="color"
                :image-url="imageUrl"
              />
            </div>
            <div class="preview-title">{{ previewTitle }}</div>
          </div>
        </div>
      </div>

      <div v-if="error" class="form-error">{{ error }}</div>
      <div v-if="saveSuccess" class="form-success">
        Appearance settings saved.
      </div>

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
  margin: 0 0 12px;
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
  color: var(--ui-text);
}
.section-hint {
  color: var(--ui-dim);
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 16px;
}
.field {
  margin-bottom: 20px;
}
.field > span {
  display: block;
  font-size: 0.85rem;
  color: var(--ui-text);
  margin-bottom: 8px;
}
.field-sublabel {
  color: var(--ui-faint);
  font-size: 0.76rem;
  line-height: 1.5;
  margin: 0 0 10px;
}
.color-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.color-input {
  width: 44px;
  height: 44px;
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  background: var(--ui-bg);
  padding: 2px;
  cursor: pointer;
}
.color-text {
  width: 100px;
  background: var(--ui-bg);
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 8px 10px;
  font: inherit;
  font-size: 0.85rem;
}
.image-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.image-preview {
  width: 44px;
  height: 44px;
  border-radius: var(--ui-radius-control);
  background: var(--ui-bg);
  border: 1px solid var(--ui-border-strong);
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ui-faint);
  flex-shrink: 0;
}
.upload-label {
  cursor: pointer;
}
.hidden-input {
  display: none;
}
.preview-row {
  display: flex;
}
.preview-card {
  width: 180px;
  max-width: 100%;
  border-radius: var(--ui-radius-control);
  padding: 6px;
  background: var(--ui-bg);
}
.preview-cover {
  position: relative;
  aspect-ratio: 2 / 3;
  border-radius: 6px;
  overflow: hidden;
  background: var(--ui-surface);
  margin-bottom: 6px;
}
.preview-title {
  color: var(--ui-text);
  font-size: 0.72rem;
  text-align: center;
}
.preview-card.badge-glow {
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--badge-color) 55%, transparent),
    0 0 22px 2px color-mix(in srgb, var(--badge-color) 45%, transparent);
}
.preview-card.badge-border {
  box-shadow: 0 0 0 2px var(--badge-color);
}
.preview-art {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.form-error {
  color: var(--ui-error);
  font-size: 13px;
  background: var(--ui-danger-soft);
  border: 1px solid color-mix(in srgb, var(--ui-error) 30%, transparent);
  border-radius: var(--ui-radius-control);
  padding: 8px 10px;
  margin-bottom: 14px;
}
.form-success {
  color: var(--ui-good);
  font-size: 13px;
  background: var(--ui-good-soft);
  border: 1px solid color-mix(in srgb, var(--ui-good) 30%, transparent);
  border-radius: var(--ui-radius-control);
  padding: 8px 10px;
  margin-bottom: 14px;
}
.primary-button {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 11px 20px;
  font-weight: 600;
  cursor: pointer;
}
.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.secondary-button {
  background: color-mix(in srgb, var(--ui-text) 8%, transparent);
  color: var(--ui-text);
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 9px 14px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.secondary-button:hover {
  background: color-mix(in srgb, var(--ui-text) 14%, transparent);
}
</style>
