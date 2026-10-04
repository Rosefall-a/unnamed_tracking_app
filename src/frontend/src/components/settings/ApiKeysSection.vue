<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  createApiKey,
  fetchApiKeys,
  revokeApiKey,
  type ApiKeySummary,
} from "../../services/auth";

const keys = ref<ApiKeySummary[]>([]);
const name = ref("");
const isLoading = ref(true);
const isCreating = ref(false);
const error = ref("");
const createdKey = ref("");

async function loadKeys() {
  isLoading.value = true;
  error.value = "";
  try {
    keys.value = await fetchApiKeys();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to load API keys.";
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
  try {
    const result = await createApiKey(keyName);
    createdKey.value = result.api_key;
    name.value = "";
    await loadKeys();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to create API key.";
  } finally {
    isCreating.value = false;
  }
}

async function handleRevoke(key: ApiKeySummary) {
  if (
    !window.confirm(`Revoke the API key "${key.name}"? This cannot be undone.`)
  ) {
    return;
  }

  error.value = "";
  try {
    await revokeApiKey(key.id);
    keys.value = keys.value.filter((item) => item.id !== key.id);
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to revoke API key.";
  }
}

onMounted(loadKeys);
</script>

<template>
  <section class="section">
    <div class="section-header">
      <div>
        <h2>API Keys</h2>
        <p>
          Generate keys for external apps and integrations such as the Playnite
          plugin.
        </p>
      </div>
    </div>

    <div class="notice">
      API keys grant access to your account. Keep them private and revoke any
      key you no longer use.
    </div>

    <form class="create-form" @submit.prevent="handleCreate">
      <label for="api-key-name">Key name</label>
      <div class="create-row">
        <input
          id="api-key-name"
          v-model="name"
          type="text"
          maxlength="100"
          placeholder="e.g. Playnite"
          autocomplete="off"
        />
        <button type="submit" :disabled="isCreating || !name.trim()">
          {{ isCreating ? "Generating…" : "Generate key" }}
        </button>
      </div>
    </form>

    <div v-if="createdKey" class="created-key">
      <strong>API key created</strong>
      <p>Copy this key now. It will not be shown again.</p>
      <code>{{ createdKey }}</code>
      <button type="button" class="secondary" @click="createdKey = ''">
        Done
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="keys">
      <h3>Your keys</h3>
      <p v-if="isLoading" class="muted">Loading…</p>
      <p v-else-if="keys.length === 0" class="muted">
        No API keys have been created.
      </p>
      <div v-else class="key-list">
        <div v-for="key in keys" :key="key.id" class="key-row">
          <div>
            <strong>{{ key.name }}</strong>
            <span>
              {{ key.key_prefix }} · created
              {{ new Date(key.created_at * 1000).toLocaleDateString() }}
            </span>
          </div>
          <button type="button" class="danger" @click="handleRevoke(key)">
            Revoke
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.section {
  color: var(--ui-text);
}

.section-header {
  margin-bottom: 24px;
}

h2 {
  margin: 0 0 12px;
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
  color: var(--ui-text);
}

h3 {
  margin: 0 0 12px;
  font-size: 1rem;
}

p {
  margin: 0;
  color: color-mix(in srgb, var(--ui-text) 68%, transparent);
  line-height: 1.5;
}

.notice {
  margin-bottom: 24px;
  padding: 12px 14px;
  border: 1px solid color-mix(in srgb, var(--ui-text) 10%, transparent);
  border-radius: var(--ui-radius-control);
  background: color-mix(in srgb, var(--ui-text) 3.5%, transparent);
  color: color-mix(in srgb, var(--ui-text) 75%, transparent);
  font-size: 0.9rem;
}

.create-form {
  margin-bottom: 32px;
}

label {
  display: block;
  margin-bottom: 8px;
  font-size: 0.9rem;
  font-weight: 600;
}

.create-row {
  display: flex;
  gap: 10px;
}

input {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--ui-border);
  border-radius: 7px;
  background: var(--ui-bg);
  color: var(--ui-text);
  font: inherit;
}

input:focus {
  outline: none;
  border-color: var(--ui-accent);
}

button {
  padding: 10px 14px;
  border: 0;
  border-radius: 7px;
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.secondary {
  margin-top: 12px;
  background: color-mix(in srgb, var(--ui-text) 10%, transparent);
  color: var(--ui-text);
}

.danger {
  border: 1px solid rgba(255, 143, 143, 0.25);
  background: transparent;
  color: var(--ui-error);
}

.created-key {
  margin-bottom: 32px;
  padding: 16px;
  border: 1px solid color-mix(in srgb, var(--ui-text) 14%, transparent);
  border-radius: 9px;
  background: color-mix(in srgb, var(--ui-text) 4%, transparent);
}

.created-key strong {
  display: block;
  margin-bottom: 4px;
}

.created-key p {
  margin-bottom: 12px;
}

code {
  display: block;
  overflow-x: auto;
  padding: 12px;
  border-radius: 6px;
  background: var(--ui-bg);
  color: var(--ui-text);
  font:
    0.85rem/1.5 ui-monospace,
    SFMono-Regular,
    Menlo,
    monospace;
  user-select: all;
}

.error {
  margin-bottom: 20px;
  color: #ff9d9d;
}

.muted {
  font-size: 0.9rem;
}

.keys {
  padding-top: 8px;
}

.key-list {
  border-top: 1px solid var(--ui-border);
}

.key-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid var(--ui-border);
}

.key-row strong,
.key-row span {
  display: block;
}

.key-row span {
  margin-top: 4px;
  color: color-mix(in srgb, var(--ui-text) 50%, transparent);
  font-size: 0.82rem;
}

@media (max-width: 600px) {
  .create-row {
    flex-direction: column;
  }

  .key-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
