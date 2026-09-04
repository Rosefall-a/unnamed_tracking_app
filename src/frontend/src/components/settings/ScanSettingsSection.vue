<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchScanSettings, updateScanSettings } from '../../services/settings'
import type { ScanProvider } from '../../services/settings'
import ToggleButton from './ToggleButton.vue'

const PROVIDER_LABELS: Record<ScanProvider, string> = {
  Steam: 'Steam',
  IGDB: 'IGDB',
  GiantBomb: 'Giant Bomb',
  RetroAchievements: 'RetroAchievements',
  SteamGridDB: 'SteamGridDB (art only)',
  ScreenScraper: 'ScreenScraper (art only)',
  HowLongToBeat: 'HowLongToBeat (time to beat only)',
}

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const saveSuccess = ref(false)

const providerOrder = ref<ScanProvider[]>([
  'Steam',
  'IGDB',
  'GiantBomb',
  'RetroAchievements',
  'SteamGridDB',
  'ScreenScraper',
  'HowLongToBeat',
])
const saveDeveloper = ref(true)
const savePublisher = ref(true)
const saveSeries = ref(true)
const saveTags = ref(true)
const saveFeatures = ref(true)
const saveDescription = ref(true)
const saveAgeRating = ref(true)
const saveReleaseDate = ref(true)
const saveTimeToBeat = ref(true)

onMounted(async () => {
  try {
    const settings = await fetchScanSettings()
    providerOrder.value = settings.provider_order
    saveDeveloper.value = settings.save_developer
    savePublisher.value = settings.save_publisher
    saveSeries.value = settings.save_series
    saveTags.value = settings.save_tags
    saveFeatures.value = settings.save_features
    saveDescription.value = settings.save_description
    saveAgeRating.value = settings.save_age_rating
    saveReleaseDate.value = settings.save_release_date
    saveTimeToBeat.value = settings.save_time_to_beat
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load scan settings'
  } finally {
    loading.value = false
  }
})

function moveProvider(index: number, direction: -1 | 1) {
  const target = index + direction
  if (target < 0 || target >= providerOrder.value.length) return
  const next = [...providerOrder.value]
  ;[next[index], next[target]] = [next[target], next[index]]
  providerOrder.value = next
}

async function save() {
  saving.value = true
  error.value = null
  saveSuccess.value = false
  try {
    await updateScanSettings({
      provider_order: providerOrder.value,
      save_developer: saveDeveloper.value,
      save_publisher: savePublisher.value,
      save_series: saveSeries.value,
      save_tags: saveTags.value,
      save_features: saveFeatures.value,
      save_description: saveDescription.value,
      save_age_rating: saveAgeRating.value,
      save_release_date: saveReleaseDate.value,
      save_time_to_beat: saveTimeToBeat.value,
    })
    saveSuccess.value = true
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to save scan settings'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Scan Settings</h2>
    <p class="section-hint">
      Controls how future metadata searches behave — which provider is checked first, and
      which fields a search result is allowed to save onto a game.
    </p>

    <p v-if="loading">Loading…</p>
    <template v-else>
      <div class="field-block">
        <span class="field-label">Provider order</span>
        <ol class="provider-list">
          <li v-for="(provider, index) in providerOrder" :key="provider" class="provider-item">
            <span>{{ PROVIDER_LABELS[provider] }}</span>
            <div class="provider-arrows">
              <button type="button" :disabled="index === 0" @click="moveProvider(index, -1)">↑</button>
              <button type="button" :disabled="index === providerOrder.length - 1" @click="moveProvider(index, 1)">↓</button>
            </div>
          </li>
        </ol>
      </div>

      <div class="field-block">
        <span class="field-label">Fields to save from a search result</span>
        <p class="field-sublabel">
          Turn a field off to leave it untouched by search/refresh — useful if you keep your
          own values for something and don't want them overwritten.
        </p>
        <div class="refresh-options">
          <ToggleButton v-model="saveDeveloper" label="Developer">
            <strong>Developer</strong> — the studio that made the game
          </ToggleButton>
          <ToggleButton v-model="savePublisher" label="Publisher">
            <strong>Publisher</strong> — who released it
          </ToggleButton>
          <ToggleButton v-model="saveSeries" label="Series">
            <strong>Series</strong> — franchise name, e.g. "Halo"
          </ToggleButton>
          <ToggleButton v-model="saveTags" label="Tags">
            <strong>Tags</strong> — Steam genre tags (RPG, Strategy, etc.)
          </ToggleButton>
          <ToggleButton v-model="saveFeatures" label="Features">
            <strong>Features</strong> — Steam categories (Co-op, Controller support, etc.)
          </ToggleButton>
          <ToggleButton v-model="saveDescription" label="Description">
            <strong>Description</strong> — the "About This Game" text and screenshots
          </ToggleButton>
          <ToggleButton v-model="saveAgeRating" label="Age rating">
            <strong>Age rating</strong> — e.g. "17+"
          </ToggleButton>
          <ToggleButton v-model="saveReleaseDate" label="Release date">
            <strong>Release date</strong>
          </ToggleButton>
          <ToggleButton v-model="saveTimeToBeat" label="Time to beat">
            <strong>Time to beat</strong> — main story hours, from HowLongToBeat
          </ToggleButton>
        </div>
      </div>

      <div v-if="error" class="form-error">{{ error }}</div>
      <div v-if="saveSuccess" class="form-success">Scan settings saved.</div>

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
.field-block {
  margin-bottom: 20px;
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
