<script setup lang="ts">
import UiModal from "./UiModal.vue";

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
  <UiModal :title="(editing ? 'Edit ' : 'Add ') + noun" @close="emit('closed')">
    <div class="media-form-fields">
      <p v-if="error" class="ui-error-box" role="alert">{{ error }}</p>
      <slot />
    </div>
    <template #footer>
      <button
        v-if="editing"
        type="button"
        class="ui-btn ui-btn-danger"
        :disabled="deleting || saving"
        @click="emit('delete')"
      >
        {{ deleting ? "Deleting…" : "Delete" }}
      </button>
      <span class="media-form-spacer" />
      <button type="button" class="ui-btn ui-btn-ghost" @click="emit('closed')">
        Cancel
      </button>
      <button
        type="button"
        class="ui-btn ui-btn-primary"
        :disabled="saving || deleting"
        @click="emit('save')"
      >
        {{ saving ? "Saving…" : editing ? "Save Changes" : "Add " + noun }}
      </button>
    </template>
  </UiModal>
</template>
<style scoped>
.media-form-fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.media-form-spacer {
  flex: 1;
}
</style>
