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
    const result = await fetchDeploymentSettings();
    Object.assign(values, result.runtime);
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
    restartRequired.value = true;
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
    <p class="hint">
      These settings are stored in the database, so normal application configuration no longer
      requires editing <code>.env</code>. Provider credentials, OIDC, and SMTP have their own
      Settings sections.
    </p>

    <div v-if="loading">Loading…</div>
    <template v-else>
      <label class="toggle">
        <input v-model="values.auth_cookie_secure" type="checkbox" />
        <span>
          <strong>Secure authentication cookies</strong>
          <small>Enable when the application is served over HTTPS. A restart is required after changing this.</small>
        </span>
      </label>

      <div class="grid">
        <label>
          <span>Maximum upload size (MB)</span>
          <input v-model.number="values.max_upload_size_mb" type="number" min="1" />
          <small>Images and other standard uploads.</small>
        </label>
        <label>
          <span>Maximum clip size (MB)</span>
          <input v-model.number="values.max_clip_size_mb" type="number" min="1" />
          <small>Video clips and soundtrack uploads.</small>
        </label>
        <label>
          <span>Maximum world/modpack size (MB)</span>
          <input v-model.number="values.max_world_save_size_mb" type="number" min="1" />
          <small>World saves and modpack archives.</small>
        </label>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="saved" class="success">Saved. Upload limits apply immediately; restart the application to apply cookie-security changes.</p>
      <button :disabled="saving" @click="save">{{ saving ? "Saving…" : "Save application settings" }}</button>
      <p v-if="restartRequired" class="hint">A restart is recommended after changing the secure-cookie setting.</p>
    </template>
  </section>
</template>

<style scoped>
.section{display:flex;flex-direction:column;gap:16px}.hint{color:#999;font-size:13px;line-height:1.5}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.grid label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.grid input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.grid input:focus{outline:none;border-color:#d68a34}.grid small,.toggle small{color:#777;font-size:12px;line-height:1.4}.toggle{display:flex;gap:10px;align-items:flex-start;color:#ddd}.toggle input{margin-top:3px}.toggle span{display:flex;flex-direction:column;gap:4px}code{color:#ddd}.section h2{margin:0;color:#fff}button{align-self:flex-start;background:#d68a34;border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}button:disabled{opacity:.6}.error{color:#fca5a5}.success{color:#86efac}@media(max-width:900px){.grid{grid-template-columns:1fr}}
</style>
