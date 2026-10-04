<script setup lang="ts">
defineProps<{ title: string; description?: string; eyebrow?: string }>();
</script>

<template>
  <header class="page-header">
    <div class="page-heading">
      <p v-if="eyebrow" class="page-eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p v-if="description" class="page-description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: var(--ui-space-8);
}
.page-heading {
  min-width: 0;
  max-width: 100%;
}
h1 {
  color: var(--ui-text);
  font: var(--ui-weight-title) var(--ui-font-title)/1.2 var(--ui-font-family);
  letter-spacing: -0.035em;
  margin: 0 0 8px;
  overflow-wrap: anywhere;
}
.page-description {
  color: var(--ui-dim);
  font-size: var(--ui-font-body);
  line-height: 1.5;
  max-width: 65ch;
}
.page-eyebrow {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  letter-spacing: 0.08em;
  margin-bottom: 10px;
  overflow-wrap: anywhere;
}
.page-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
@media (max-width: 760px) {
  .page-header {
    align-items: flex-start;
    margin-bottom: 24px;
  }
}
</style>
