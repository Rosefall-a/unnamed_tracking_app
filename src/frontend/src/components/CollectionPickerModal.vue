<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchGames, addGameToCollection } from '../services/games'
import type { Game } from '../types/game'

const props = defineProps<{
  game: Game
}>()

const emit = defineEmits<{
  close: []
  added: []
}>()

const query = ref('')
const saving = ref(false)
const error = ref<string | null>(null)
const loading = ref(true)
const allNames = ref<string[]>([])

onMounted(async () => {
  try {
    const games = await fetchGames()
    const set = new Set<string>()
    games.forEach((g) => g.collections.forEach((c) => set.add(c)))
    try {
      const raw = localStorage.getItem('manualCollections')
      const manual: string[] = raw ? JSON.parse(raw) : []
      manual.forEach((n) => set.add(n))
    } catch {
      // ignore — manual collections are a nice-to-have, not required here
    }
    allNames.value = Array.from(set).sort()
  } finally {
    loading.value = false
  }
})

const availableNames = computed(() => allNames.value.filter((n) => !props.game.collections.includes(n)))

const filteredNames = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return availableNames.value
  return availableNames.value.filter((n) => n.toLowerCase().includes(q))
})

const exactMatch = computed(() =>
  allNames.value.some((n) => n.toLowerCase() === query.value.trim().toLowerCase()),
)

async function pick(name: string) {
  saving.value = true
  error.value = null
  try {
    await addGameToCollection(props.game.id, name)
    emit('added')
    emit('close')
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to add to collection'
  } finally {
    saving.value = false
  }
}

function createAndAdd() {
  const name = query.value.trim()
  if (!name) return
  pick(name)
}
</script>

<template>
  <div class="picker-backdrop" @click.self="emit('close')">
    <div class="picker-modal">
      <h3>Add "{{ game.title }}" to a collection</h3>
      <input
        v-model="query"
        type="text"
        class="picker-input"
        placeholder="Search or create a collection…"
        autofocus
        @keyup.enter="!exactMatch && query.trim() ? createAndAdd() : undefined"
      />

      <div v-if="error" class="picker-error">{{ error }}</div>

      <div class="picker-list">
        <p v-if="loading" class="picker-empty">Loading…</p>
        <template v-else>
          <button
            v-if="query.trim() && !exactMatch"
            type="button"
            class="picker-item picker-create"
            :disabled="saving"
            @click="createAndAdd"
          >
            + Create "{{ query.trim() }}"
          </button>
          <button
            v-for="name in filteredNames"
            :key="name"
            type="button"
            class="picker-item"
            :disabled="saving"
            @click="pick(name)"
          >
            {{ name }}
          </button>
          <p v-if="!filteredNames.length && (!query.trim() || exactMatch)" class="picker-empty">
            {{ availableNames.length ? 'No matches.' : 'No collections yet — type a name to create one.' }}
          </p>
        </template>
      </div>

      <div class="picker-actions">
        <button type="button" class="secondary-button" @click="emit('close')">Cancel</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.picker-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 70;
}
.picker-modal {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 22px;
  width: 100%;
  max-width: 380px;
  color: #fff;
  font-family: system-ui, sans-serif;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
}
.picker-modal h3 {
  margin: 0 0 14px;
  font-size: 1.05rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.picker-input {
  width: 100%;
  box-sizing: border-box;
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 10px 12px;
  font: inherit;
  font-size: 14px;
  margin-bottom: 12px;
}
.picker-input:focus {
  outline: none;
  border-color: #d68a34;
}
.picker-error {
  color: #fca5a5;
  font-size: 13px;
  margin-bottom: 10px;
}
.picker-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 260px;
  overflow-y: auto;
  margin-bottom: 16px;
}
.picker-item {
  background: none;
  border: none;
  color: #ddd;
  text-align: left;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.15s ease;
}
.picker-item:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.08);
}
.picker-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.picker-create {
  color: #d68a34;
  font-weight: 600;
}
.picker-empty {
  color: #777;
  font-size: 13px;
  margin: 0;
  padding: 6px 12px;
}
.picker-actions {
  display: flex;
  justify-content: flex-end;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 9px 18px;
  font-weight: 600;
  cursor: pointer;
}
</style>
