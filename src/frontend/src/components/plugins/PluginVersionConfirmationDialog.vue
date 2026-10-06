<script setup lang="ts">
import UiModal from "../UiModal.vue";
import AppIcon from "../AppIcon.vue";
defineProps<{ installed: string; candidate: string; downgrade: boolean }>();
defineEmits<{ confirm: []; cancel: [] }>();
</script>

<template>
  <UiModal
    :title="downgrade ? 'Confirm downgrade' : 'Confirm same-version update'"
    @close="$emit('cancel')"
  >
    <section class="version-warning" role="alert">
      <AppIcon name="warning" />
      <div>
        <strong>{{
          downgrade
            ? "You are about to downgrade this plugin."
            : "This is the same version as the installed plugin."
        }}</strong>
        <p>Installed v{{ installed }} → selected v{{ candidate }}.</p>
        <p v-if="downgrade">
          The selected release will be pinned and automatic updates disabled.
          Existing data is retained; an older release may handle that data
          differently.
        </p>
        <p v-else>
          The selected package will be applied again. Existing data and the
          current update policy are retained.
        </p>
        <p>Are you sure you want to apply this package?</p>
      </div>
    </section>
    <template #footer>
      <button
        type="button"
        class="ui-btn ui-btn-ghost"
        @click="$emit('cancel')"
      >
        Cancel
      </button>
      <button
        type="button"
        class="ui-btn ui-btn-primary"
        @click="$emit('confirm')"
      >
        {{ downgrade ? "Confirm downgrade" : "Apply this version again" }}
      </button>
    </template>
  </UiModal>
</template>

<style scoped>
.version-warning {
  display: flex;
  align-items: flex-start;
  gap: var(--ui-space-3);
  padding: var(--ui-space-4);
  border: 1px solid var(--ui-warning);
  border-radius: var(--ui-radius-card);
  background: var(--ui-warning-soft);
  color: var(--ui-warning);
  overflow-wrap: anywhere;
}
.version-warning > svg {
  flex-shrink: 0;
}
p {
  margin: var(--ui-space-3) 0 0;
}
</style>
