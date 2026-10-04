<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import {
  fetchDeploymentSettings,
  updateDeploymentSettings,
} from "../../services/deploymentSettings";
import TrustedProxyControls from "./TrustedProxyControls.vue";

const fields = [
  ["steamgriddb_api_key", "SteamGridDB API key"],
  ["retroachievements_api_key", "RetroAchievements API key"],
  ["giantbomb_api_key", "Giant Bomb API key"],
  ["igdb_client_id", "IGDB client ID"],
  ["igdb_client_secret", "IGDB client secret"],
  ["screenscraper_ssid", "ScreenScraper app username"],
  ["screenscraper_sspassword", "ScreenScraper app password"],
  ["screenscraper_devid", "ScreenScraper developer ID"],
  ["screenscraper_devpassword", "ScreenScraper developer password"],
  ["xbox_client_id", "Xbox client ID"],
  ["xbox_client_secret", "Xbox client secret"],
] as const;

const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);
const saved = ref(false);
const providers = reactive<Record<string, string>>({});
const configured = reactive<Record<string, boolean>>({});
const deploymentSettings = ref<Awaited<ReturnType<typeof fetchDeploymentSettings>> | null>(null);
const realIpHeader = ref("");
const realIpTrustedProxies = ref("");

onMounted(async () => {
  try {
    const result = await fetchDeploymentSettings();
    deploymentSettings.value = result;
    realIpHeader.value = result.real_ip.header;
    realIpTrustedProxies.value = result.real_ip.trusted_proxies;
    for (const [key, value] of Object.entries(result.providers)) {
      if (key.endsWith("_configured"))
        configured[key.replace(/_configured$/, "")] = Boolean(value);
      else if (typeof value === "string") providers[key] = value;
    }
    for (const [key, value] of Object.entries(result.provider_locks)) {
      if (value) configured[key] = true;
    }
  } catch (err) {
    error.value =
      err instanceof Error
        ? err.message
        : "Failed to load server integrations.";
  } finally {
    loading.value = false;
  }
});

async function save() {
  saving.value = true;
  error.value = null;
  saved.value = false;
  try {
    const payload: Record<string, string> = {};
    for (const [key] of fields)
      if (providers[key]) payload[key] = providers[key];
    payload.nginx_realip_header = realIpHeader.value;
    payload.nginx_realip_trusted_proxies = realIpTrustedProxies.value;
    const result = await updateDeploymentSettings(payload);
    for (const [key, value] of Object.entries(result.providers))
      if (typeof value === "string") providers[key] = value;
    saved.value = true;
  } catch (err) {
    error.value =
      err instanceof Error
        ? err.message
        : "Failed to save server integrations.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="section">
    <h2>Server integrations</h2>
    <p class="hint">
      Admin-only deployment credentials for metadata and external services.
      Secrets are encrypted in the database and are never returned to the
      browser after saving. Values supplied by the deployment environment are
      managed there and cannot be replaced from this page.
    </p>
    <div v-if="loading">Loading…</div>
    <template v-else>
      <div class="grid">
        <label v-for="[key, label] in fields" :key="key"
          ><span>{{ label }}</span
          ><input
            v-model="providers[key]"
            :type="
              key.includes('secret') ||
              key.includes('password') ||
              key.includes('api_key')
                ? 'password'
                : 'text'
            "
             :placeholder="
              deploymentSettings?.provider_locks[key] ?? false
                ? 'Managed by deployment environment'
                : configured[key]
                  ? 'Already saved — enter a new value to replace it'
                  : ''
            "
            :disabled="deploymentSettings?.provider_locks[key] ?? false"
        /></label>
      </div>
      <section class="proxy-section">
        <h3>Client IP / reverse proxy</h3>
        <p class="hint">Nginx trusts only loopback by default. Add Cloudflare, local/private, CGNAT/VPS, or custom ranges when they are actually proxy networks for this deployment. Environment values take precedence and are locked.</p>
        <label><span>Real client IP header</span><input v-model="realIpHeader" :disabled="deploymentSettings?.real_ip.locked.header ?? false" /></label>
        <TrustedProxyControls v-model="realIpTrustedProxies" :disabled="deploymentSettings?.real_ip.locked.trusted_proxies ?? false" />
      </section>
      <p class="hint">
        OpenID Connect / SSO has its own tab so authentication settings can be
        managed separately.
      </p>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="saved" class="success">Saved.</p>
      <button :disabled="saving" @click="save">
        {{ saving ? "Saving…" : "Save server integrations" }}
      </button>
    </template>
  </section>
</template>

<style scoped>
.section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.hint {
  color: #999;
  font-size: 13px;
  line-height: 1.5;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #ccc;
  font-size: 13px;
}
.grid input {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 10px;
  font: inherit;
}
.grid input:focus {
  outline: none;
  border-color: #d68a34;
}
h2 {
  margin: 0;
  color: #fff;
}
.proxy-section{display:flex;flex-direction:column;gap:12px;border-top:1px solid #333;padding-top:18px}
.proxy-section h3{margin:0;color:#fff}
.proxy-section label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}
.proxy-section label input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}
button {
  align-self: flex-start;
  background: #d68a34;
  border: 0;
  border-radius: 8px;
  padding: 10px 14px;
  font-weight: 600;
  cursor: pointer;
}
button:disabled {
  opacity: 0.6;
}
.error {
  color: #fca5a5;
}
.success {
  color: #86efac;
}
@media (max-width: 760px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
