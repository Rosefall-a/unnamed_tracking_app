<script setup lang="ts">
// The TV show edit form. The form itself is shared with movies and anime (see
// MediaFormModal); this keeps the props and events the TV show page uses.
import MediaFormModal from "./MediaFormModal.vue";
import type { TVShow } from "../types/tv_show";

defineProps<{
  show?: TVShow | null;
}>();

const emit = defineEmits<{
  saved: [show: TVShow];
  deleted: [showId: string];
  closed: [];
}>();
</script>

<template>
  <MediaFormModal
    kind="tv"
    :item="show"
    @saved="(item) => emit('saved', item as TVShow)"
    @deleted="(id) => emit('deleted', id)"
    @closed="emit('closed')"
  />
</template>
