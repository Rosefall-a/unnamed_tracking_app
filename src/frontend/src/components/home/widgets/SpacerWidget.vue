<script setup lang="ts">
// Empty space, for keeping widgets apart or holding a gap open (the page closes
// gaps up otherwise). Nothing shows on the page; while editing, the layout draws
// it as a hatched box so it can be found and resized.
import type { WidgetProps } from "../../../home/registry";

defineProps<WidgetProps>();
</script>

<template>
  <div class="spacer-box" aria-hidden="true"></div>
</template>

<style scoped>
.spacer-box {
  width: 100%;
  height: 100%;
}
</style>
