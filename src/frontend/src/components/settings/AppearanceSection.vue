<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import SettingsCard from "./SettingsCard.vue";
import SettingsRow from "./SettingsRow.vue";
import SettingsSwitch from "./SettingsSwitch.vue";
import CoverMarks from "../CoverMarks.vue";
import TrophyIcon from "../TrophyIcon.vue";
import {
  fetchAppearanceSettings,
  updateAppearanceSettings,
  uploadBadgeImage,
  deleteBadgeImage,
} from "../../services/appearanceSettings";
import { loadAppearanceSettings } from "../../state/appearance";
import {
  MARKS,
  activeMarks,
  type CompletionMark,
} from "../../utils/completionMarks";
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

// colors or badge shows one card, so Display can sit between them
withDefaults(defineProps<{ part?: "all" | "colors" | "badge" }>(), {
  part: "all",
});

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
const error = ref<string | null>(null);
const color = ref("#d4af37");
const imageUrl = ref<string | null>(null);

onMounted(async () => {
  try {
    const settings = await fetchAppearanceSettings();
    color.value = settings.completion_badge_color;
    imageUrl.value = settings.completion_badge_image_url;
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Could not load appearance settings";
  } finally {
    loading.value = false;
  }
});

// Marks and the pop-up save the moment they change, like the rest of Settings.
// Only the newest save's answer is applied, so quick clicks never undo each
// other when an older answer arrives late.
let saveSeq = 0;
async function savePrefs(changes: {
  completion_marks?: CompletionMark[];
  notify_game_complete?: boolean;
}) {
  const seq = ++saveSeq;
  const before = preferences.value;
  preferences.value = { ...before, ...changes };
  try {
    const { prefs } = await queuePreferences(changes);
    if (seq !== saveSeq) return;
    preferences.value = { ...preferences.value, ...prefs };
    error.value = null;
  } catch (err) {
    if (seq !== saveSeq) return;
    preferences.value = before;
    error.value =
      err instanceof Error ? err.message : "Could not save that change";
  }
}
function toggleMark(id: CompletionMark) {
  const next = new Set(activeMarks.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  void savePrefs({
    completion_marks: MARKS.map((m) => m.id).filter((m) => next.has(m)),
  });
}

// the colour is saved a moment after the last change
let colorTimer: number | undefined;
function setBadgeColor(value: string) {
  color.value = value;
  if (!/^#[0-9a-fA-F]{6}$/.test(value)) return;
  window.clearTimeout(colorTimer);
  colorTimer = window.setTimeout(async () => {
    try {
      await updateAppearanceSettings({
        completion_badge_color: value.toLowerCase(),
      });
      await loadAppearanceSettings();
      error.value = null;
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : "Could not save the colour";
    }
  }, 400);
}

// the preview uses the same marks a real cover does, with a sample count
const previewEntry = {
  total: 66,
  unlocked: 66,
  rarest: { name: "Rarest unlock", icon_url: null, percent: 1.4 },
};
const has = (m: CompletionMark) => activeMarks.value.has(m);
const previewVars = computed(() => {
  const c = color.value.toLowerCase();
  const gold = c === "#d4af37" || !/^#[0-9a-f]{6}$/.test(c);
  const hi = gold ? "#f1cd6a" : `color-mix(in srgb, ${c} 72%, #fff)`;
  return {
    "--mk": gold ? "#e9be5a" : c,
    "--mk-hi": hi,
    "--mk-ring": `color-mix(in srgb, ${hi} 55%, transparent)`,
  };
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
  <SettingsCard
    v-if="part !== 'badge'"
    title="Colours"
    description="Changes show right away and follow your account to every browser."
  >
    <template #actions>
      <button
        v-if="anyColor"
        type="button"
        class="st-btn"
        @click="changeColors({})"
      >
        Reset to default
      </button>
    </template>
    <SettingsRow
      v-for="key in THEME_COLOR_KEYS"
      :key="key"
      :label="THEME_COLOR_INFO[key].label"
      :hint="THEME_COLOR_INFO[key].hint"
    >
      <div class="color-row">
        <template v-if="key === 'accent'">
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
        </template>
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
          class="st-btn reset"
          @click="resetColor(key)"
        >
          Reset
        </button>
      </div>
    </SettingsRow>
    <p v-if="colorsError" class="st-error">{{ colorsError }}</p>
  </SettingsCard>

  <SettingsCard
    v-if="part !== 'colors'"
    title="100% games"
    description="How a game with every achievement unlocked stands out."
  >
    <p v-if="loading" class="st-muted">Loading…</p>
    <template v-else>
      <SettingsRow
        label="100% mark on covers"
        hint="Pick any mix. Shown on games where every achievement is unlocked."
        stack
      >
        <div class="marks">
          <button
            v-for="m in MARKS"
            :key="m.id"
            type="button"
            class="mark"
            :class="{ on: has(m.id) }"
            :aria-pressed="has(m.id)"
            :title="m.hint"
            @click="toggleMark(m.id)"
          >
            {{ m.label }}
          </button>
        </div>
      </SettingsRow>
      <SettingsRow label="Preview" hint="Hover it to see the Foil sheen">
        <div class="mk-preview" :style="previewVars">
          <div class="game-card-wrap">
            <div class="game-card">
              <div class="cover">
                <span class="cover-art" aria-hidden="true"></span>
                <CoverMarks
                  :marks="activeMarks"
                  :entry="previewEntry"
                  :image-url="imageUrl"
                />
              </div>
            </div>
            <div class="card-info">
              <b class="p-title" :class="{ 'gold-t': has('gold_title') }"
                >Your 100% game</b
              >
              <span v-if="has('caption')" class="tro"><TrophyIcon />100%</span>
              <span v-else-if="has('gold_title')" class="tro"
                ><TrophyIcon />66 / 66</span
              >
              <span v-else class="plain">Mastered</span>
            </div>
          </div>
        </div>
      </SettingsRow>
      <SettingsRow
        v-if="activeMarks.size"
        label="Colour"
        hint="The gold the marks are drawn in"
      >
        <div class="color-row">
          <input
            :value="color"
            type="color"
            class="color-input"
            aria-label="Mark colour"
            @input="setBadgeColor(($event.target as HTMLInputElement).value)"
          />
          <input
            :value="color"
            type="text"
            class="color-text"
            maxlength="7"
            aria-label="Mark colour hex value"
            @change="setBadgeColor(($event.target as HTMLInputElement).value)"
          />
          <button
            v-if="color.toLowerCase() !== '#d4af37'"
            type="button"
            class="st-btn reset"
            @click="setBadgeColor('#d4af37')"
          >
            Reset
          </button>
        </div>
      </SettingsRow>
      <SettingsRow
        v-if="has('seal')"
        label="Seal picture"
        hint="Replaces the trophy in the Seal. Use a small square or round image."
      >
        <div class="image-row">
          <div
            class="image-preview"
            :style="imageUrl ? { backgroundImage: `url(${imageUrl})` } : {}"
          >
            <TrophyIcon v-if="!imageUrl" />
          </div>
          <label class="st-btn upload-label">
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
            class="st-btn"
            :disabled="uploading"
            @click="removeImage"
          >
            Remove
          </button>
        </div>
      </SettingsRow>
      <SettingsRow
        label="Pop-up when a game hits 100%"
        hint="Also adds a line to the bell"
      >
        <SettingsSwitch
          :model-value="preferences.notify_game_complete"
          label="Pop-up when a game hits 100%"
          @update:model-value="savePrefs({ notify_game_complete: $event })"
        />
      </SettingsRow>
      <p v-if="error" class="st-error">{{ error }}</p>
    </template>
  </SettingsCard>
</template>

<style scoped>
/* 100% marks: chips you can mix, and a cover that shows the mix */
.marks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.mark {
  border: 1px solid var(--ui-border);
  border-radius: 999px;
  padding: 5px 12px;
  background: transparent;
  color: var(--ui-text-soft);
  font: inherit;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
.mark:hover {
  border-color: var(--ui-border-strong);
  color: var(--ui-heading);
}
.mark.on {
  border-color: var(--ui-accent-line);
  background: color-mix(in srgb, var(--ui-accent) 14%, transparent);
  color: var(--ui-accent-bright);
}
.mk-preview {
  width: 150px;
}
.mk-preview .game-card {
  position: relative;
  border-radius: 10px;
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1);
}
.mk-preview .game-card:hover {
  transform: translateY(-3px);
}
.mk-preview .cover {
  position: relative;
  aspect-ratio: 2 / 3;
  border-radius: 10px;
  overflow: hidden;
  background: var(--ui-surface-2);
}
.cover-art {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(
      circle at 30% 25%,
      color-mix(in srgb, var(--ui-accent) 45%, transparent),
      transparent 55%
    ),
    linear-gradient(160deg, #2a3446, #121722 70%);
}
.mk-preview .card-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 8px;
  min-width: 0;
}
.p-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--ui-text);
}
.p-title.gold-t {
  color: var(--mk-hi);
}
.plain {
  font-size: 0.7rem;
  color: var(--ui-faint);
}
.tro {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.7rem;
  font-variant-numeric: tabular-nums;
}
.tro {
  color: var(--mk);
  font-weight: 600;
}
.image-preview :deep(svg) {
  width: 16px;
  height: 16px;
  color: var(--mk-hi, #f1cd6a);
}

.color-row .reset {
  padding: 6px 10px;
}
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
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
  gap: 6px 8px;
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
  width: 30px;
  height: 30px;
  border: 1px solid #3a3a3a;
  border-radius: 7px;
  cursor: pointer;
  padding: 0;
}
.swatch.on {
  outline: 2px solid var(--ui-text);
  outline-offset: 1px;
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
