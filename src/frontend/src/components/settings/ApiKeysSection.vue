<script setup lang="ts">
import { onMounted, ref } from "vue";
import SettingsCard from "./SettingsCard.vue";
import PasswordInput from "../PasswordInput.vue";
import {
  createApiKey,
  fetchApiKeys,
  revokeApiKey,
  type ApiKeySummary,
} from "../../services/auth";
import { useConfirm } from "../../state/dialog";

const confirm = useConfirm();
const keys = ref<ApiKeySummary[]>([]);
const name = ref("");
const isLoading = ref(true);
const isCreating = ref(false);
const error = ref("");
const createdKey = ref("");
const copyStatus = ref<"idle" | "copied" | "failed">("idle");

async function loadKeys() {
  isLoading.value = true;
  error.value = "";
  try {
    keys.value = await fetchApiKeys();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Could not load API keys.";
  } finally {
    isLoading.value = false;
  }
}

async function handleCreate() {
  const keyName = name.value.trim();
  if (!keyName) return;

  isCreating.value = true;
  error.value = "";
  createdKey.value = "";
  copyStatus.value = "idle";
  try {
    const result = await createApiKey(keyName);
    createdKey.value = result.api_key;
    name.value = "";
    await loadKeys();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Could not create API key.";
  } finally {
    isCreating.value = false;
  }
}

async function handleRevoke(key: ApiKeySummary) {
  if (
    !(await confirm({
      title: "Revoke API key",
      message: `Revoke the API key "${key.name}"? This cannot be undone.`,
      confirmLabel: "Revoke",
      danger: true,
    }))
  ) {
    return;
  }

  error.value = "";
  const previousKeys = keys.value;
  // Remove it immediately so a successful revoke cannot leave a stale active
  // key visible while the server refresh completes.
  keys.value = previousKeys.filter((candidate) => candidate.id !== key.id);

  try {
    await revokeApiKey(key.id);
    // Refresh from the server so the UI reflects the persisted revocation.
    // The backend only returns non-revoked keys, so a revoked key stays gone.
    await loadKeys();
  } catch (err) {
    keys.value = previousKeys;
    error.value =
      err instanceof Error ? err.message : "Could not revoke API key.";
  }
}

async function copyCreatedKey() {
  if (!createdKey.value) return;
  copyStatus.value = "idle";
  try {
    if (!navigator.clipboard?.writeText) {
      throw new Error("Clipboard access is unavailable.");
    }
    await navigator.clipboard.writeText(createdKey.value);
    copyStatus.value = "copied";
  } catch {
    copyStatus.value = "failed";
  }
}

onMounted(loadKeys);
</script>

<template>
  <SettingsCard
    title="New key"
    description="For other apps that talk to your library, such as the Playnite plugin. A key can do anything you can, so give each app its own and revoke the ones you stop using."
  >
    <form @submit.prevent="handleCreate">
      <label class="st-flabel" for="api-key-name">Name</label>
      <input
        id="api-key-name"
        v-model="name"
        class="st-field"
        type="text"
        maxlength="100"
        placeholder="e.g. Playnite on desktop"
        autocomplete="off"
      />
      <div class="st-btns create-actions">
        <button
          type="submit"
          class="st-btn primary"
          :disabled="isCreating || !name.trim()"
        >
          {{ isCreating ? "Creating…" : "Create key" }}
        </button>
      </div>
    </form>

    <div v-if="createdKey" class="st-note created-key">
      <div class="created-inner">
        <strong>Key created</strong>
        <span>Copy it now. It will not be shown again.</span>
        <PasswordInput
          v-model="createdKey"
          mode="replace"
          readonly
          autocomplete="off"
          input-aria-label="Generated API key"
        />
        <div class="st-btns">
          <button type="button" class="st-btn primary" @click="copyCreatedKey">
            {{
              copyStatus === "copied"
                ? "Copied"
                : copyStatus === "failed"
                  ? "Copy failed"
                  : "Copy key"
            }}
          </button>
          <button
            type="button"
            class="st-btn"
            @click="
              createdKey = '';
              copyStatus = 'idle';
            "
          >
            Done
          </button>
        </div>
      </div>
    </div>
    <p v-if="error" class="st-error">{{ error }}</p>
  </SettingsCard>

  <SettingsCard title="Your keys">
    <p v-if="isLoading" class="st-muted">Loading…</p>
    <p v-else-if="keys.length === 0" class="st-muted">No keys yet.</p>
    <div v-for="key in keys" v-else :key="key.id" class="st-list-row">
      <div class="st-lbl">
        <strong>{{ key.name }}</strong>
        <span>
          {{ key.key_prefix }} · created
          {{ new Date(key.created_at * 1000).toLocaleDateString() }} ·
          {{
            key.last_used_at
              ? `last used ${new Date(key.last_used_at * 1000).toLocaleDateString()}`
              : "never used"
          }}
        </span>
      </div>
      <button type="button" class="st-btn danger" @click="handleRevoke(key)">
        Revoke
      </button>
    </div>
  </SettingsCard>
</template>

<style scoped>
.create-actions {
  margin-top: 14px;
}
.created-inner {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.created-inner strong {
  color: var(--ui-heading);
}
</style>
