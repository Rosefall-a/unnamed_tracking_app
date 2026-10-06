<script setup lang="ts">
// The dialog around the Movie, TV and Anime forms: title, close button,
// an error line, the fields (the default slot), and Delete / Cancel / Save.
// Each form keeps its own fields and decides what saving and deleting do.
defineProps<{
  // "Movie", "TV Show" or "Anime", for the title and the Add button
  noun: string;
  editing: boolean;
  saving: boolean;
  deleting: boolean;
  error: string | null;
}>();

const emit = defineEmits<{
  closed: [];
  save: [];
  delete: [];
}>();
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('closed')">
    <div class="modal" role="dialog" :aria-label="noun">
      <div class="modal-head">
        <h2>{{ editing ? "Edit" : "Add" }} {{ noun }}</h2>
        <button type="button" class="close-btn" @click="emit('closed')">
          &times;
        </button>
      </div>

      <div class="modal-body">
        <p v-if="error" class="error-text">{{ error }}</p>
        <slot />
      </div>

      <div class="modal-foot">
        <button
          v-if="editing"
          type="button"
          class="delete-btn"
          :disabled="deleting || saving"
          @click="emit('delete')"
        >
          {{ deleting ? "Deleting…" : "Delete" }}
        </button>
        <div class="modal-foot-spacer"></div>
        <button type="button" class="secondary-button" @click="emit('closed')">
          Cancel
        </button>
        <button
          type="button"
          class="primary-btn"
          :disabled="saving || deleting"
          @click="emit('save')"
        >
          {{ saving ? "Saving…" : editing ? "Save Changes" : `Add ${noun}` }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--ui-z-modal);
  background: rgba(8, 6, 4, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.modal {
  width: 100%;
  max-width: 480px;
  max-height: 86vh;
  display: flex;
  flex-direction: column;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 30px 70px -20px rgba(0, 0, 0, 0.8);
  color: #fff;
  font-family: system-ui, sans-serif;
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid #2a2a2a;
}

.modal-head h2 {
  margin: 0;
  font-size: 1.05rem;
}

.close-btn {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  width: 32px;
  height: 32px;
  margin: -3px -7px -3px 0;
  border-radius: 50%;
  font-size: 1.2rem;
  line-height: 1;
}

.close-btn:hover {
  color: #d68a34;
}

.modal-body {
  padding: 18px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.error-text {
  color: #fca5a5;
  font-size: 0.85rem;
  margin: 0;
}

.modal-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  border-top: 1px solid #2a2a2a;
}

.modal-foot-spacer {
  flex: 1;
}

.primary-btn {
  background: #d68a34;
  color: #121212;
  border: none;
  border-radius: 8px;
  padding: 9px 18px;
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.secondary-button {
  background: #111;
  border: 1px solid #2a2a2a;
  color: #ccc;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 0.85rem;
  cursor: pointer;
}

.delete-btn {
  background: none;
  border: 1px solid #5c2a2a;
  color: #fca5a5;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 0.85rem;
  cursor: pointer;
}

.delete-btn:hover {
  background: #2a1414;
}

.delete-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
