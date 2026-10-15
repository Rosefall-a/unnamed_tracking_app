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
import { preferences } from "../../state/preferences";
import { queuePreferences } from "../../services/preferences";
import {
  ACCENT_PRESETS,
  THEME_COLOR_INFO,
  THEME_COLOR_KEYS,
  applyThemeColors,
  cacheThemeColors,
} from "../../state/themeColors";
import type { ThemeColorKey, ThemeColors } from "../../state/themeColors";

// ---- the app's colours ----
const colors = ref<ThemeColors>({ ...preferences.value.theme_colors });
const colorsError = ref<string | null>(null);
let colorsTimer: number | undefined;
function changeColors(next: ThemeColors) {
  colors.value = next;
  // shown straight away, saved a moment after the last change
  applyThemeColors(next);
  cacheThemeColors(next);
  window.clearTimeout(colorsTimer);
  colorsTimer = window.setTimeout(async () => {
    try {
      const { prefs } = await queuePreferences({ theme_colors: next });
      preferences.value = {
        ...preferences.value,
        theme_colors: prefs.theme_colors,
      };
      colorsError.value = null;
    } catch (e) {
      colorsError.value =
        e instanceof Error ? e.message : "Could not save your colours.";
    }
  }, 500);
}
function setColor(key: ThemeColorKey, value: string) {
  if (/^#[0-9a-fA-F]{6}$/.test(value))
    changeColors({ ...colors.value, [key]: value.toLowerCase() });
}
function resetColor(key: ThemeColorKey) {
  const { [key]: _removed, ...rest } = colors.value;
  void _removed;
  changeColors(rest);
}
const anyColor = computed(() => Object.keys(colors.value).length > 0);

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
      err instanceof Error ? err.message : "Could not load appearance settings";
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
      err instanceof Error ? err.message : "Could not save appearance settings";
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
      err instanceof Error ? err.message : "Could not upload badge image";
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
      err instanceof Error ? err.message : "Could not remove badge image";
  } finally {
    uploading.value = false;
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Appearance</h2>

    <h3 class="sub">Colors</h3>
    <p class="section-hint">
      Change the colors the whole app uses. Changes show right away and follow
      your account.
    </p>
    <div class="colors">
      <div v-for="key in THEME_COLOR_KEYS" :key="key" class="color-line">
        <div class="color-info">
          <strong>{{ THEME_COLOR_INFO[key].label }}</strong>
          <span>{{ THEME_COLOR_INFO[key].hint }}</span>
        </div>
        <div class="color-row">
          <input
            type="color"
            class="color-input"
            :value="colors[key] ?? THEME_COLOR_INFO[key].fallback"
            :aria-label="`${THEME_COLOR_INFO[key].label} color`"
            @input="setColor(key, ($event.target as HTMLInputElement).value)"
          />
          <input
            type="text"
            class="color-text"
            maxlength="7"
            :value="colors[key] ?? THEME_COLOR_INFO[key].fallback"
            :aria-label="`${THEME_COLOR_INFO[key].label} hex value`"
            @change="setColor(key, ($event.target as HTMLInputElement).value)"
          />
          <button
            v-if="colors[key]"
            type="button"
            class="reset"
            @click="resetColor(key)"
          >
            Reset
          </button>
        </div>
        <div v-if="key === 'accent'" class="presets">
          <button
            v-for="c in ACCENT_PRESETS"
            :key="c"
            type="button"
            class="swatch"
            :class="{
              on: (colors.accent ?? THEME_COLOR_INFO.accent.fallback) === c,
            }"
            :style="{ background: c }"
            :aria-label="`Use ${c} as the accent`"
            @click="setColor('accent', c)"
          ></button>
        </div>
      </div>
      <button
        v-if="anyColor"
        type="button"
        class="reset-all"
        @click="changeColors({})"
      >
        Reset all colors
      </button>
      <p v-if="colorsError" class="colors-error">{{ colorsError }}</p>
    </div>

    <h3 class="sub">Mastered games</h3>
    <p class="section-hint">
      How Mastered (100% complete) games are highlighted in the library.
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
          <input v-model="color" type="color" class="color-input" />
          <input v-model="color" type="text" class="color-text" maxlength="7" />
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
          Replaces the default trophy icon. Use a small square or round image.
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
              <div
                v-if="usesPlacement"
                class="preview-badge"
                :class="[style, placement]"
              >
                <img
                  v-if="imageUrl"
                  :src="imageUrl"
                  alt=""
                  class="preview-badge-image"
                />
                <svg
                  v-else
                  viewBox="0 0 24 24"
                  width="14"
                  height="14"
                  fill="currentColor"
                >
                  <path
                    d="M12 2l2.4 6.6L21 9l-5 4.6L17.4 21 12 17.3 6.6 21 8 13.6 3 9l6.6-.4z"
                  />
                </svg>
              </div>
            </div>
            <div class="preview-title">Mastered game</div>
          </div>
        </div>
      </div>

      <div v-if="error" class="form-error">{{ error }}</div>
      <div v-if="saveSuccess" class="form-success">Saved</div>

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
  border-left: 3px solid var(--ui-accent);
  font-size: 1rem;
  color: var(--ui-heading);
}
.section-hint {
  color: var(--ui-dim-3);
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
  color: var(--ui-text-soft);
  margin-bottom: 8px;
}
.field-sublabel {
  color: var(--ui-faint-2);
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
  width: 40px;
  height: 36px;
  border: 1px solid var(--ui-border-strong);
  border-radius: 8px;
  background: var(--ui-bg-2);
  padding: 2px;
  cursor: pointer;
}
.color-text {
  width: 100px;
  background: var(--ui-bg-2);
  border: 1px solid var(--ui-border-strong);
  border-radius: 8px;
  color: var(--ui-heading);
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
  border-radius: 8px;
  background: var(--ui-bg-2);
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
  width: 140px;
  border-radius: 10px;
  padding: 6px;
  background: var(--ui-bg-2);
}
.preview-cover {
  position: relative;
  aspect-ratio: 2 / 3;
  border-radius: 6px;
  background: linear-gradient(135deg, var(--ui-border), var(--ui-surface));
  margin-bottom: 6px;
}
.preview-title {
  color: var(--ui-text-soft);
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
.preview-badge {
  position: absolute;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--badge-color);
}
.preview-badge.top-left {
  top: 6px;
  left: 6px;
}
.preview-badge.top-right {
  top: 6px;
  right: 6px;
}
.preview-badge.bottom-left {
  bottom: 6px;
  left: 6px;
}
.preview-badge.bottom-right {
  bottom: 6px;
  right: 6px;
}
.preview-badge.corner_badge {
  background: rgba(20, 20, 20, 0.55);
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--badge-color) 60%, transparent);
}
.preview-badge-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.form-error {
  color: var(--ui-error-text);
  font-size: 13px;
  background: color-mix(in srgb, var(--ui-danger) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-danger) 30%, transparent);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 14px;
}
.form-success {
  color: var(--ui-good-text);
  font-size: 13px;
  background: color-mix(in srgb, var(--ui-success) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-success) 30%, transparent);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 14px;
}
.primary-button {
  background: var(--ui-accent);
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
.secondary-button {
  background: color-mix(in srgb, var(--ui-wash-base) 8%, transparent);
  color: var(--ui-heading);
  border: none;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.secondary-button:hover {
  background: color-mix(in srgb, var(--ui-wash-base) 14%, transparent);
}
.sub {
  margin: 22px 0 6px;
  font-size: 0.92rem;
  color: var(--ui-text);
}
.colors {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 8px;
}
.color-line {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) auto;
  align-items: center;
  gap: 8px 16px;
}
.color-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.color-info strong {
  font-size: 0.86rem;
  color: var(--ui-text);
}
.color-info span {
  font-size: 0.76rem;
  color: var(--ui-faint);
}
.presets {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.swatch {
  width: 26px;
  height: 26px;
  border: 2px solid transparent;
  border-radius: 50%;
  cursor: pointer;
}
.swatch.on {
  border-color: var(--ui-text);
}
.reset,
.reset-all {
  padding: 5px 10px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  background: transparent;
  color: var(--ui-dim);
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
}
.reset:hover,
.reset-all:hover {
  color: var(--ui-text);
  border-color: var(--ui-border-strong);
}
.reset-all {
  align-self: flex-start;
}
.colors-error {
  margin: 0;
  color: var(--ui-error-text);
  font-size: 0.8rem;
}
</style>
