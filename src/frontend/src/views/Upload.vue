<script setup lang="ts">
import AccountChip from "../components/AccountChip.vue";
import PageHeader from "../components/PageHeader.vue";
import UploadSection from "../components/settings/UploadSection.vue";
</script>

<template>
  <main class="upload-page">
    <AccountChip fixed />
    <PageHeader title="Upload" />
    <div class="upload-content"><UploadSection standalone /></div>
  </main>
</template>

<style scoped>
.upload-page {
  box-sizing: border-box;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 92px 40px 40px;
}
.upload-content {
  padding: 24px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
}
@media (max-width: 760px) {
  .upload-page {
    padding: 88px 16px 24px;
  }
  .upload-content {
    padding: 20px 16px;
  }
}
</style>
