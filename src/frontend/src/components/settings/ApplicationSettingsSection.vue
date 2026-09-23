<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { fetchDeploymentSettings, updateDeploymentSettings } from "../../services/deploymentSettings";

const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);
const saved = ref(false);
const restartRequired = ref(false);

const values = reactive({
  auth_cookie_secure: false,
  max_upload_size_mb: 15,
  max_clip_size_mb: 500,
  max_world_save_size_mb: 2000,
});

onMounted(async () => {
  try {
    Object.assign(values, (await fetchDeploymentSettings()).runtime);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load application settings.";
  } finally {
    loading.value = false;
  }
});

async function save() {
  saving.value = true;
  error.value = null;
  saved.value = false;
  restartRequired.value = false;
  try {
    await updateDeploymentSettings({ ...values });
    saved.value = true;
    restartRequired.value = values.auth_cookie_secure !== undefined;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to save application settings.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="section">
    <h2>Application settings</h2>
    <p class="hint">These deployment-wide values are stored in the database and applied at startup. Upload limits apply to new requests immediately; cookie-security changes require a restart.</p>
    <div v-if="loading">Loading…</div>
    <template v-else>
      <label class="toggle">
        <input v-model="values.auth_cookie_secure" type="checkbox" />
        <span><strong>Secure authentication cookies</strong><small>Enable when the browser-facing application is served over HTTPS.</small></span>
      </label>
      <div class="grid">
        <label><span>Maximum upload size (MB)</span><input v-model.number="values.max_upload_size_mb" type="number" min="1" /></label>
        <label><span>Maximum clip size (MB)</span><input v-model.number="values.max_clip_size_mb" type="number" min="1" /></label>
        <label><span>Maximum world/modpack size (MB)</span><input v-model.number="values.max_world_save_size_mb" type="number" min="1" /></label>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="saved" class="success">Application settings saved.</p>
      <p v-if="restartRequired" class="hint">Restart the backend after changing secure-cookie behaviour.</p>
      <button :disabled="saving" @click="save">{{ saving ? "Saving…" : "Save application settings" }}</button>
    </template>
  </section>
</template>

<style scoped>
.section{display:flex;flex-direction:column;gap:16px}.hint{color:#999;font-size:13px;line-height:1.5}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.grid label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.grid input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.toggle{display:flex;gap:10px;align-items:flex-start;color:#ddd}.toggle span{display:flex;flex-direction:column;gap:4px}.toggle small{color:#777;font-size:12px}.error{color:#fca5a5}.success{color:#86efac}button{align-self:flex-start;background:#d68a34;border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}button:disabled{opacity:.6}@media(max-width:900px){.grid{grid-template-columns:1fr}}
</style>
