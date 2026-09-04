<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    description: string
    plannedFeatures?: string[]
  }>(),
  { plannedFeatures: () => [] },
)
</script>

<template>
  <section class="settings-section">
    <h2>{{ title }}</h2>
    <div class="coming-soon">
      <svg class="coming-soon-icon" viewBox="0 0 24 24" width="64" height="64" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 8v4l2.5 2.5" />
      </svg>
      <span class="soon-badge">Coming soon</span>
      <p>{{ description }}</p>
      <ul v-if="plannedFeatures.length" class="planned-list">
        <li v-for="feature in plannedFeatures" :key="feature">{{ feature }}</li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 16px;
  font-size: 1rem;
  color: #fff;
}
.coming-soon {
  background: #111;
  border: 1px dashed #3a3a3a;
  border-radius: 10px;
  padding: 32px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.coming-soon-icon {
  color: #3a3a3a;
  margin-bottom: 14px;
}
.soon-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  color: #999;
  background: rgba(255, 255, 255, 0.06);
  padding: 3px 10px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 12px;
}
.coming-soon p {
  margin: 0 0 16px;
  color: #999;
  font-size: 0.85rem;
  line-height: 1.6;
  max-width: 440px;
}
.planned-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
}
.planned-list li {
  color: #ccc;
  font-size: 0.82rem;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  padding: 8px 14px;
  min-width: 260px;
}
.planned-list li::before {
  content: '→ ';
  color: #d68a34;
}
</style>
