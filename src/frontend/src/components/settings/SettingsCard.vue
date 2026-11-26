<script setup lang="ts">
// One card on a Settings tab: a title, an optional line under it, and the
// settings inside. The actions slot sits on the right of the title.
defineProps<{ title?: string; description?: string; warn?: boolean }>();
</script>

<template>
  <section class="st-card" :class="{ warn }">
    <div v-if="title || $slots.actions" class="st-card-head">
      <h3 v-if="title">{{ title }}</h3>
      <slot name="actions" />
    </div>
    <p v-if="description || $slots.description" class="st-desc">
      <slot name="description">{{ description }}</slot>
    </p>
    <slot />
  </section>
</template>
