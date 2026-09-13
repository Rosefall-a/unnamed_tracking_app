<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { fetchDeploymentSettings, updateDeploymentSettings } from "../../services/deploymentSettings";

const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);
const saved = ref(false);
const providers = reactive<Record<string, string>>({});
const configured = reactive<Record<string, boolean>>({});
const oidc = reactive({ issuer_url: "", client_id: "", client_secret: "", scopes: "openid profile email", redirect_uri: "", groups_claim: "groups", admin_group: "" });

const fields = [
  ["steamgriddb_api_key", "SteamGridDB API key"], ["retroachievements_api_key", "RetroAchievements API key"],
  ["giantbomb_api_key", "Giant Bomb API key"], ["igdb_client_id", "IGDB client ID"], ["igdb_client_secret", "IGDB client secret"],
  ["screenscraper_ssid", "ScreenScraper app username"], ["screenscraper_sspassword", "ScreenScraper app password"],
  ["screenscraper_devid", "ScreenScraper developer ID"], ["screenscraper_devpassword", "ScreenScraper developer password"],
  ["xbox_client_id", "Xbox client ID"], ["xbox_client_secret", "Xbox client secret"],
] as const;

onMounted(async () => {
  try {
    const result = await fetchDeploymentSettings();
    for (const [key, value] of Object.entries(result.providers)) {
      if (key.endsWith("_configured")) configured[key.replace(/_configured$/, "")] = Boolean(value);
      else if (typeof value === "string") providers[key] = value;
    }
    oidc.issuer_url = result.oidc.issuer_url ?? "";
    oidc.client_id = result.oidc.client_id ?? "";
    oidc.scopes = result.oidc.scopes ?? "openid profile email";
    oidc.redirect_uri = result.oidc.redirect_uri ?? "";
    oidc.groups_claim = result.oidc.groups_claim ?? "groups";
    oidc.admin_group = result.oidc.admin_group ?? "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load server integrations.";
  } finally { loading.value = false; }
});

async function save() {
  saving.value = true; error.value = null; saved.value = false;
  try {
    const payload: Record<string, string> = {};
    for (const [key] of fields) if (providers[key]) payload[key] = providers[key];
    if (oidc.issuer_url) payload.oidc_issuer_url = oidc.issuer_url;
    if (oidc.client_id) payload.oidc_client_id = oidc.client_id;
    if (oidc.client_secret) payload.oidc_client_secret = oidc.client_secret;
    if (oidc.scopes) payload.oidc_scopes = oidc.scopes;
    if (oidc.redirect_uri) payload.oidc_redirect_uri = oidc.redirect_uri;
    payload.oidc_groups_claim = oidc.groups_claim.trim() || "groups";
    payload.oidc_admin_group = oidc.admin_group.trim();
    const result = await updateDeploymentSettings(payload);
    for (const [key, value] of Object.entries(result.providers)) if (typeof value === "string") providers[key] = value;
    oidc.client_secret = "";
    saved.value = true;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to save server integrations.";
  } finally { saving.value = false; }
}
</script>

<template>
  <section class="section">
    <h2>Server integrations</h2>
    <p class="hint">Admin-only deployment credentials. Secrets are encrypted in the database and are never returned to the browser after saving. Existing environment variables remain supported as fallbacks.</p>
    <div v-if="loading">Loading…</div>
    <template v-else>
      <div class="grid">
        <label v-for="[key, label] in fields" :key="key"><span>{{ label }}</span><input v-model="providers[key]" :type="key.includes('secret') || key.includes('password') || key.includes('api_key') ? 'password' : 'text'" :placeholder="configured[key] ? 'Already saved — enter a new value to replace it' : ''" /></label>
      </div>
      <h3>OpenID Connect / SSO</h3>
      <p class="hint">Configure SSO entirely from the browser. The client secret stays on the backend. If an admin group is set, membership in that IdP group controls the application administrator role at each SSO login.</p>
      <div class="grid">
        <label><span>Issuer URL</span><input v-model="oidc.issuer_url" placeholder="https://login.example.com/realms/archive" /></label>
        <label><span>Client ID</span><input v-model="oidc.client_id" /></label>
        <label><span>Client secret</span><input v-model="oidc.client_secret" type="password" placeholder="Leave blank to keep the saved secret" /></label>
        <label><span>Scopes</span><input v-model="oidc.scopes" /></label>
        <label><span>Redirect URI</span><input v-model="oidc.redirect_uri" placeholder="https://archive.example.com/api/auth/oidc/callback" /></label>
        <label><span>Groups claim</span><input v-model="oidc.groups_claim" placeholder="groups" /></label>
        <label><span>Admin group</span><input v-model="oidc.admin_group" placeholder="archive-admins" /></label>
      </div>
      <p class="hint">Leave Admin group blank to keep administrator status managed locally. The groups claim can be changed for providers that expose groups under a custom claim name.</p>
      <p v-if="error" class="error">{{ error }}</p><p v-if="saved" class="success">Saved.</p>
      <button :disabled="saving" @click="save">{{ saving ? "Saving…" : "Save server integrations" }}</button>
    </template>
  </section>
</template>

<style scoped>
.section{display:flex;flex-direction:column;gap:16px}.hint{color:#999;font-size:13px;line-height:1.5}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.grid label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.grid input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.grid input:focus{outline:none;border-color:#d68a34}h2,h3{margin:0;color:#fff}button{align-self:flex-start;background:#d68a34;border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}button:disabled{opacity:.6}.error{color:#fca5a5}.success{color:#86efac}@media(max-width:760px){.grid{grid-template-columns:1fr}}
</style>
