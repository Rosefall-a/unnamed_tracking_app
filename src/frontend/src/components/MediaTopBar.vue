<script setup lang="ts">
// The Media-area bar: AppTopBar with the Movies / TV Shows / Anime / Collections
// switcher on the left, and on the right whatever the page adds (its
// `actions` slot).
import AppTopBar from "./AppTopBar.vue";
import MediaKindSwitch from "./MediaKindSwitch.vue";

defineProps<{
  active: "movie" | "tv" | "anime" | "lists";
}>();

</script>

<template>
  <AppTopBar>
    <MediaKindSwitch :active="active" />
    <template #actions>
      <slot name="actions" />
    </template>
  </AppTopBar>
</template>
