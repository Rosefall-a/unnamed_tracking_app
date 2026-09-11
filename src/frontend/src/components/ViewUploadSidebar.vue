<script setup lang="ts">
defineProps<{ modelValue: "view" | "upload" }>();
defineEmits<{ "update:modelValue": ["view" | "upload"] }>();
</script>

<template>
  <nav class="vu-sidebar">
    <button
      type="button"
      class="vu-item"
      :class="{ active: modelValue === 'view' }"
      @click="$emit('update:modelValue', 'view')"
    >
      <svg
        viewBox="0 0 24 24"
        width="15"
        height="15"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
      View
    </button>
    <button
      type="button"
      class="vu-item"
      :class="{ active: modelValue === 'upload' }"
      @click="$emit('update:modelValue', 'upload')"
    >
      <svg
        viewBox="0 0 24 24"
        width="15"
        height="15"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M12 3v12" />
        <path d="M7 8l5-5 5 5" />
        <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
      </svg>
      Upload
    </button>
  </nav>
</template>

<style scoped>
.vu-sidebar {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 130px;
  flex-shrink: 0;
}
.vu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  border-radius: 8px;
  padding: 9px 12px;
  color: #999;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.vu-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.vu-item.active {
  background: rgba(214, 138, 52, 0.16);
  color: #d68a34;
}
</style>
