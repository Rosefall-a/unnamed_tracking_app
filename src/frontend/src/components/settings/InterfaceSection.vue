<script setup lang="ts">
import { ref, watch } from 'vue'
import SegmentedControl from './SegmentedControl.vue'
import ToggleButton from './ToggleButton.vue'

type ViewMode = 'cards' | 'list' | 'detail'
type SortBy = 'name' | 'recent' | 'rating' | 'playtime'

const defaultViewMode = ref<ViewMode>((localStorage.getItem('gameLibraryViewMode') as ViewMode) || 'cards')
const defaultSort = ref<SortBy>((localStorage.getItem('gameLibraryDefaultSort') as SortBy) || 'name')
const compactMode = ref(localStorage.getItem('compactMode') === 'true')

const viewModeOptions = [
  { value: 'cards', label: 'Cards' },
  { value: 'list', label: 'List' },
  { value: 'detail', label: 'List + preview' },
]
const sortOptions = [
  { value: 'name', label: 'Name' },
  { value: 'recent', label: 'Recently added' },
  { value: 'rating', label: 'Rating' },
  { value: 'playtime', label: 'Most played' },
]

watch(defaultViewMode, (mode) => localStorage.setItem('gameLibraryViewMode', mode))
watch(defaultSort, (sort) => localStorage.setItem('gameLibraryDefaultSort', sort))
watch(compactMode, (enabled) => {
  localStorage.setItem('compactMode', String(enabled))
  document.documentElement.classList.toggle('compact', enabled)
})
</script>

<template>
  <section class="settings-section">
    <h2>User Interface</h2>
    <p class="section-hint">
      These are the defaults used the next time you open the Games page — they don't change
      anything on a page you already have open.
    </p>

    <div class="field">
      <span>Default view mode</span>
      <SegmentedControl
        :model-value="defaultViewMode"
        :options="viewModeOptions"
        @update:model-value="defaultViewMode = $event as ViewMode"
      />
    </div>

    <div class="field">
      <span>Default sort</span>
      <SegmentedControl
        :model-value="defaultSort"
        :options="sortOptions"
        @update:model-value="defaultSort = $event as SortBy"
      />
    </div>

    <ToggleButton v-model="compactMode" label="Compact mode">
      <strong>Compact mode</strong> — tighter spacing across the app
    </ToggleButton>
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
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 0.85rem;
  color: #ccc;
  margin-bottom: 18px;
}
</style>
