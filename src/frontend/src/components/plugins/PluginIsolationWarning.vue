<script setup lang="ts">
import { computed, ref } from "vue";
import UiModal from "../UiModal.vue";
import type { RuntimeCapabilities } from "../../services/plugins";

const props = defineProps<{
  runtime: RuntimeCapabilities;
  busy: boolean;
  error: string;
}>();
const emit = defineEmits<{ approve: []; cancel: [] }>();
const open = ref(false);
const acknowledged = ref(false);
const needsApproval = computed(
  () =>
    props.runtime.available !== false &&
    props.runtime.bubblewrap_available === false &&
    !props.runtime.reduced_isolation_allowed,
);
function review() {
  acknowledged.value = false;
  open.value = true;
}
function close() {
  open.value = false;
  acknowledged.value = false;
}
defineExpose({ review, close });
</script>

<template>
  <aside
    v-if="
      runtime.available === false ||
      (!runtime.sandbox_available && !runtime.reduced_isolation_env_override)
    "
    class="runtime-notice"
  >
    <strong>{{
      runtime.available === false
        ? "Plugin runtime unavailable"
        : runtime.reduced_isolation_allowed
          ? "Plugins use reduced isolation"
          : "Reduced isolation needs approval"
    }}</strong>
    <p v-if="runtime.available === false">
      Installed plugins remain listed. Isolation cannot be checked until the
      runtime reconnects.
    </p>
    <p v-else>
      Bubblewrap is unavailable. Plugins can run in separate processes with
      available resource limits after an administrator acknowledges the weaker
      isolation for this server. Package verification and permission review
      still apply.
    </p>
    <p v-if="runtime.reduced_isolation_acknowledged" class="acknowledged">
      An administrator acknowledged reduced isolation for this server. This
      warning remains visible while Bubblewrap is unavailable.
    </p>
    <button
      v-if="needsApproval"
      type="button"
      class="ui-btn ui-btn-primary"
      :disabled="busy"
      @click="review"
    >
      Review reduced isolation
    </button>
    <p v-if="runtime.last_error && runtime.available !== false">
      {{ runtime.last_error }}
    </p>
    <a
      href="https://github.com/Rosefall-a/unnamed_tracking_app/blob/plugin-manager/wiki/docs/development/plugin-runtime.md"
      target="_blank"
      rel="noopener noreferrer"
      >Runtime setup and Bubblewrap help</a
    >
  </aside>
  <UiModal
    v-if="open"
    title="Allow reduced plugin isolation"
    :dismissible="!busy"
    @close="
      close();
      emit('cancel');
    "
  >
    <p>
      This server cannot use Bubblewrap. Plugins will have fewer filesystem and
      namespace restrictions. Only install plugins you trust. Their declared
      permissions, package checks and available process limits still apply.
    </p>
    <p>
      Approval covers all plugins on this server and survives restarts. You can
      withdraw it in Plugin Manager settings. NONBUBBLE_ENV is optional.
    </p>
    <label class="acknowledgement">
      <input v-model="acknowledged" type="checkbox" :disabled="busy" />
      I understand that reduced isolation is less secure.
    </label>
    <p v-if="error" role="alert" class="ui-error">{{ error }}</p>
    <template #footer>
      <button
        class="ui-btn ui-btn-ghost"
        :disabled="busy"
        @click="
          close();
          emit('cancel');
        "
      >
        Cancel
      </button>
      <button
        class="ui-btn ui-btn-primary"
        :disabled="busy || !acknowledged"
        @click="emit('approve')"
      >
        {{ busy ? "Saving approval…" : "Acknowledge and allow plugins" }}
      </button>
    </template>
  </UiModal>
</template>

<style scoped>
.runtime-notice {
  margin: var(--ui-space-5) 0;
  padding: var(--ui-space-4);
  border: 1px solid var(--ui-warning);
  border-radius: var(--ui-radius-card);
  background: var(--ui-warning-soft);
  color: var(--ui-text);
  overflow-wrap: anywhere;
}
.runtime-notice p {
  line-height: 1.6;
}
.runtime-notice a {
  color: var(--ui-accent-text);
}
.acknowledged {
  color: var(--ui-dim);
}
.acknowledgement {
  display: flex;
  gap: var(--ui-space-3);
  align-items: flex-start;
  line-height: 1.6;
}
.acknowledgement input {
  margin-top: 0.3em;
}
</style>
