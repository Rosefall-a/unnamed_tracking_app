<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import SegmentedControl from './SegmentedControl.vue'
import {
  fetchAppearanceSettings,
  updateAppearanceSettings,
  uploadBadgeImage,
  deleteBadgeImage,
} from '../../services/appearanceSettings'
import type { BadgeStyle, BadgePlacement } from '../../services/appearanceSettings'
import { loadAppearanceSettings } from '../../state/appearance'

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const saveSuccess = ref(false)

const style = ref<BadgeStyle>('glow')
const color = ref('#e5e4e2')
const placement = ref<BadgePlacement>('top-right')
const imageUrl = ref<string | null>(null)

const styleOptions = [
  { value: 'none', label: 'Off' },
  { value: 'glow', label: 'Glow' },
  { value: 'border', label: 'Border' },
  { value: 'ribbon', label: 'Ribbon' },
  { value: 'corner_badge', label: 'Corner badge' },
]
const placementOptions = [
  { value: 'top-left', label: 'Top left' },
  { value: 'top-right', label: 'Top right' },
  { value: 'bottom-left', label: 'Bottom left' },
  { value: 'bottom-right', label: 'Bottom right' },
]

const usesPlacement = computed(() => style.value === 'ribbon' || style.value === 'corner_badge')
const usesImage = computed(() => style.value === 'ribbon' || style.value === 'corner_badge')

onMounted(async () => {
  try {
    const settings = await fetchAppearanceSettings()
    style.value = settings.completion_badge_style
    color.value = settings.completion_badge_color
    placement.value = settings.completion_badge_placement
    imageUrl.value = settings.completion_badge_image_url
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load appearance settings'
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  error.value = null
  saveSuccess.value = false
  try {
    await updateAppearanceSettings({
      completion_badge_style: style.value,
      completion_badge_color: color.value,
      completion_badge_placement: placement.value,
    })
    await loadAppearanceSettings()
    saveSuccess.value = true
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to save appearance settings'
  } finally {
    saving.value = false
  }
}

watch([style, color, placement], () => {
  saveSuccess.value = false
})

const uploading = ref(false)
async function onImageSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  error.value = null
  try {
    const settings = await uploadBadgeImage(file)
    imageUrl.value = settings.completion_badge_image_url
    await loadAppearanceSettings()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to upload badge image'
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function removeImage() {
  uploading.value = true
  error.value = null
  try {
    await deleteBadgeImage()
    imageUrl.value = null
    await loadAppearanceSettings()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to remove badge image'
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Appearance</h2>
    <p class="section-hint">
      How a 100%-complete (Mastered) game's card is highlighted in your library. Changes apply
      everywhere that card renders once saved.
    </p>

    <p v-if="loading">Loading…</p>
    <template v-else>
      <div class="field">
        <span>Badge style</span>
        <SegmentedControl :model-value="style" :options="styleOptions" @update:model-value="style = $event as BadgeStyle" />
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
        <p class="field-sublabel">Optional: replaces the default trophy icon. A small square/round image works best.</p>
        <div class="image-row">
          <div class="image-preview" :style="imageUrl ? { backgroundImage: `url(${imageUrl})` } : {}">
            <svg v-if="!imageUrl" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M12 2l2.4 6.6L21 9l-5 4.6L17.4 21 12 17.3 6.6 21 8 13.6 3 9l6.6-.4z" />
            </svg>
          </div>
          <label class="secondary-button upload-label">
            {{ uploading ? 'Uploading…' : 'Upload image' }}
            <input type="file" accept="image/*" class="hidden-input" :disabled="uploading" @change="onImageSelected" />
          </label>
          <button v-if="imageUrl" type="button" class="secondary-button" :disabled="uploading" @click="removeImage">
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
              <div v-if="usesPlacement" class="preview-badge" :class="[style, placement]">
                <img v-if="imageUrl" :src="imageUrl" alt="" class="preview-badge-image" />
                <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                  <path d="M12 2l2.4 6.6L21 9l-5 4.6L17.4 21 12 17.3 6.6 21 8 13.6 3 9l6.6-.4z" />
                </svg>
              </div>
            </div>
            <div class="preview-title">Mastered Game</div>
          </div>
        </div>
      </div>

      <div v-if="error" class="form-error">{{ error }}</div>
      <div v-if="saveSuccess" class="form-success">Appearance settings saved.</div>

      <button type="button" class="primary-button" :disabled="saving" @click="save">
        {{ saving ? 'Saving…' : 'Save' }}
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
.field {
  margin-bottom: 20px;
}
.field > span {
  display: block;
  font-size: 0.85rem;
  color: #ccc;
  margin-bottom: 8px;
}
.field-sublabel {
  color: #777;
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
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  background: #111;
  padding: 2px;
  cursor: pointer;
}
.color-text {
  width: 100px;
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
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
  background: #111;
  border: 1px solid #3a3a3a;
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
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
  background: #111;
}
.preview-cover {
  position: relative;
  aspect-ratio: 2 / 3;
  border-radius: 6px;
  background: linear-gradient(135deg, #2a2a2a, #1a1a1a);
  margin-bottom: 6px;
}
.preview-title {
  color: #ccc;
  font-size: 0.72rem;
  text-align: center;
}
.preview-card.badge-glow {
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--badge-color) 55%, transparent),
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
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.secondary-button:hover {
  background: rgba(255, 255, 255, 0.14);
}
</style>
