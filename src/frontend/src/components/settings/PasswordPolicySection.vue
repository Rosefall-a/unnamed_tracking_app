<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { currentUser } from "../../state/auth";
import {
  fetchPasswordPolicy,
  updatePasswordPolicy,
  type PasswordPolicy,
} from "../../services/passwordPolicy";

const policy = ref<PasswordPolicy | null>(null);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const saved = ref(false);

const canEdit = computed(() => currentUser.value?.is_admin === true);

onMounted(async () => {
  try {
    policy.value = await fetchPasswordPolicy();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to load password policy.";
  } finally {
    loading.value = false;
  }
});

async function save() {
  if (!policy.value || !canEdit.value) return;
  saving.value = true;
  saved.value = false;
  error.value = "";
  try {
    if (
      !Number.isInteger(policy.value.min_length) ||
      policy.value.min_length < 1 ||
      policy.value.min_length > 1024
    ) {
      throw new Error("Minimum password length must be between 1 and 1024.");
    }
    policy.value = await updatePasswordPolicy(policy.value);
    saved.value = true;
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to save password policy.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Password Policy</h2>
    <p class="hint">
      These rules apply to new local passwords. Administrators can change them
      here unless the deployment environment supplies password-policy values.
      Existing passwords are not changed.
    </p>
    <p v-if="loading">Loading…</p>
    <template v-else-if="policy">
      <div class="policy-form">
        <label>
          <span>Minimum password length</span>
          <input
            v-model.number="policy.min_length"
            type="number"
            min="1"
            max="1024"
            :disabled="!canEdit || saving"
          />
        </label>
        <label class="checkbox-row">
          <input
            v-model="policy.require_uppercase"
            type="checkbox"
            :disabled="!canEdit || saving"
          />
          <span>Require uppercase letter</span>
        </label>
        <label class="checkbox-row">
          <input
            v-model="policy.require_lowercase"
            type="checkbox"
            :disabled="!canEdit || saving"
          />
          <span>Require lowercase letter</span>
        </label>
        <label class="checkbox-row">
          <input
            v-model="policy.require_digit"
            type="checkbox"
            :disabled="!canEdit || saving"
          />
          <span>Require number</span>
        </label>
        <label class="checkbox-row">
          <input
            v-model="policy.require_symbol"
            type="checkbox"
            :disabled="!canEdit || saving"
          />
          <span>Require symbol</span>
        </label>
      </div>
      <p v-if="!canEdit" class="hint">
        Only administrators can change the password policy.
      </p>
      <button v-if="canEdit" type="button" :disabled="saving" @click="save">
        {{ saving ? "Saving…" : "Save password policy" }}
      </button>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="saved" class="success">Password policy saved.</p>
    </template>
    <p v-else-if="error" class="error">{{ error }}</p>
  </section>
</template>

<style scoped>
.settings-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.hint {
  color: var(--ui-dim);
  font-size: 13px;
  line-height: 1.5;
}
.policy-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 520px;
}
.policy-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--ui-text);
  font-size: 13px;
}
.policy-form input[type="number"] {
  background: var(--ui-bg);
  border: 1px solid var(--ui-border);
  border-radius: 8px;
  color: var(--ui-text);
  padding: 10px;
  font: inherit;
}
.checkbox-row {
  flex-direction: row !important;
  align-items: center;
  gap: 10px !important;
}
.checkbox-row input {
  width: auto;
}
button {
  align-self: flex-start;
  background: var(--ui-accent);
  border: 0;
  border-radius: 8px;
  color: var(--ui-on-accent);
  min-height: 44px;
  padding: 10px 14px;
  font-weight: 600;
  cursor: pointer;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.error {
  color: var(--ui-error);
}
.success {
  color: var(--ui-good);
}
h2 {
  margin: 0;
  color: var(--ui-text);
}
</style>
