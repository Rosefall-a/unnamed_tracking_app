<script setup lang="ts">
import { onMounted, ref } from "vue";
import { fetchDeploymentSettings } from "../../services/deploymentSettings";

interface StatusItem {
  label: string;
  state: "ok" | "warning" | "error";
  detail: string;
}

const items = ref<StatusItem[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

async function loadStatus() {
  loading.value = true;
  error.value = null;
  try {
    const healthResponse = await fetch("/health", { credentials: "include" });
    const deployment = await fetchDeploymentSettings();
    const smtp = deployment.smtp;
    const oidc = deployment.oidc;
    const smtpReady = Boolean(
      smtp.enabled && smtp.host && smtp.from_email && smtp.port &&
      (!smtp.username || smtp.password_configured),
    );
    const oidcConfigured = Boolean(
      oidc.client_secret_configured &&
      (oidc.named_providers?.length || (oidc.issuer_url && oidc.client_id)),
    );
    items.value = [
      {
        label: "Application",
        state: healthResponse.ok ? "ok" : "error",
        detail: healthResponse.ok ? "Application health endpoint is responding." : `Health endpoint returned HTTP ${healthResponse.status}.`,
      },
      {
        label: "Database / API",
        state: "ok",
        detail: "Authenticated deployment settings loaded successfully; database-backed API access is available.",
      },
      {
        label: "SMTP / Email",
        state: smtpReady ? "ok" : "warning",
        detail: smtpReady ? "SMTP is enabled and has the required connection settings." : smtp.enabled ? "SMTP is enabled but is not fully configured." : "SMTP is disabled.",
      },
      {
        label: "OIDC / SSO",
        state: oidcConfigured ? "ok" : "warning",
        detail: oidcConfigured ? "OIDC credentials are configured." : "OIDC is not fully configured.",
      },
    ];
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Unable to load system status.";
    items.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(loadStatus);
</script>

<template>
  <section class="settings-section">
    <h2>System status</h2>
    <p class="section-hint">Quick deployment checks for administrators. Secret values are never displayed.</p>
    <p v-if="loading">Checking system status…</p>
    <p v-else-if="error" class="form-error">{{ error }}</p>
    <div v-else class="status-list">
      <div v-for="item in items" :key="item.label" class="status-row">
        <div>
          <strong>{{ item.label }}</strong>
          <p>{{ item.detail }}</p>
        </div>
        <span class="status-badge" :class="item.state">{{ item.state === "ok" ? "Healthy" : item.state === "warning" ? "Needs attention" : "Unavailable" }}</span>
      </div>
    </div>
    <button type="button" class="secondary-button" :disabled="loading" @click="loadStatus">{{ loading ? "Checking…" : "Refresh status" }}</button>
  </section>
</template>

<style scoped>
.settings-section h2{margin:0 0 8px;padding-left:12px;border-left:3px solid #d68a34;font-size:1rem;color:#fff}.section-hint{color:#999;font-size:.82rem;line-height:1.6;margin:0 0 16px}.status-list{display:flex;flex-direction:column;gap:10px;margin-bottom:16px}.status-row{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px;border:1px solid #2a2a2a;border-radius:10px;background:#151515}.status-row strong{color:#fff;font-size:.88rem}.status-row p{margin:4px 0 0;color:#999;font-size:.78rem;line-height:1.45}.status-badge{white-space:nowrap;font-size:11px;font-weight:700;padding:4px 10px;border-radius:999px;color:#999;background:rgba(255,255,255,.06)}.status-badge.ok{color:#86efac;background:rgba(34,197,94,.1)}.status-badge.warning{color:#fcd34d;background:rgba(234,179,52,.1)}.status-badge.error{color:#fca5a5;background:rgba(220,38,38,.1)}.secondary-button{background:rgba(255,255,255,.08);color:#fff;border:0;border-radius:8px;padding:10px 18px;font-size:12px;font-weight:600;cursor:pointer}.secondary-button:disabled{opacity:.5;cursor:not-allowed}.form-error{color:#fca5a5;font-size:13px;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);border-radius:8px;padding:8px 10px}
</style>
