<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { fetchDeploymentSettings, updateDeploymentSettings } from "../../services/deploymentSettings";

const loading = ref(true);
const saving = ref(false);
const testing = ref(false);
const saved = ref(false);
const testMessage = ref<string | null>(null);
const error = ref<string | null>(null);
const smtp = reactive({
  enabled: false,
  password_reset_enabled: true,
  host: "",
  port: 587,
  username: "",
  password: "",
  use_tls: true,
  use_ssl: false,
  from_email: "",
  from_name: "Archive",
});

onMounted(async () => {
  try {
    const response = await fetchDeploymentSettings();
    const settings = response.smtp;
    smtp.enabled = settings.enabled;
    smtp.password_reset_enabled = settings.password_reset_enabled;
    smtp.host = settings.host ?? "";
    smtp.port = settings.port ?? 587;
    smtp.username = settings.username ?? "";
    smtp.use_tls = settings.use_tls;
    smtp.use_ssl = settings.use_ssl;
    smtp.from_email = settings.from_email ?? "";
    smtp.from_name = settings.from_name ?? "";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load SMTP settings.";
  } finally {
    loading.value = false;
  }
});

async function save() {
  saving.value = true;
  error.value = null;
  saved.value = false;
  testMessage.value = null;
  try {
    await updateDeploymentSettings({
      smtp_enabled: String(smtp.enabled),
      password_reset_enabled: String(smtp.password_reset_enabled),
      smtp_host: smtp.host.trim(),
      smtp_port: String(smtp.port),
      smtp_username: smtp.username.trim(),
      smtp_use_tls: String(smtp.use_tls),
      smtp_use_ssl: String(smtp.use_ssl),
      smtp_from_email: smtp.from_email.trim(),
      smtp_from_name: smtp.from_name.trim(),
      ...(smtp.password ? { smtp_password: smtp.password } : {}),
    });
    smtp.password = "";
    saved.value = true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save SMTP settings.";
  } finally {
    saving.value = false;
  }
}

async function testSmtp() {
  testing.value = true;
  error.value = null;
  testMessage.value = null;
  try {
    const response = await fetch("/api/settings/deployment/test-smtp", {
      method: "POST",
      credentials: "include",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `SMTP test failed (${response.status}).`);
    testMessage.value = data.message || "Test email sent.";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "SMTP test failed.";
  } finally {
    testing.value = false;
  }
}
</script>

<template>
  <section class="section">
    <h2>SMTP / Email</h2>
    <p class="hint">
      Configure the shared SMTP transport for password resets and future email features. SMTP
      credentials are encrypted on the backend and never returned to the browser.
    </p>

    <div v-if="loading">Loading…</div>
    <template v-else>
      <div class="feature-card">
        <label class="toggle">
          <input v-model="smtp.password_reset_enabled" type="checkbox" />
          <span>Enable password reset emails</span>
        </label>
        <p class="hint">
          Turn this off to keep SMTP configured without allowing users to request password-reset
          emails. Additional email features can use the same transport without changing this flag.
        </p>
      </div>

      <label class="toggle">
        <input v-model="smtp.enabled" type="checkbox" />
        <span>Enable SMTP email</span>
      </label>

      <div class="grid">
        <label><span>SMTP host</span><input v-model="smtp.host" placeholder="smtp.example.com" /></label>
        <label><span>Port</span><input v-model.number="smtp.port" type="number" min="1" max="65535" /></label>
        <label><span>Username</span><input v-model="smtp.username" autocomplete="off" /></label>
        <label><span>Password</span><input v-model="smtp.password" type="password" autocomplete="new-password" placeholder="Leave blank to keep saved password" /></label>
        <label><span>Sender email</span><input v-model="smtp.from_email" type="email" placeholder="noreply@example.com" /></label>
        <label><span>Sender name</span><input v-model="smtp.from_name" /></label>
      </div>

      <div class="checks">
        <label><input v-model="smtp.use_tls" type="checkbox" /> STARTTLS</label>
        <label><input v-model="smtp.use_ssl" type="checkbox" /> SSL/TLS</label>
      </div>
      <p class="hint">
        Use STARTTLS for typical port 587 configurations. Use SSL/TLS for providers that expect an
        implicit TLS connection, commonly on port 465.
      </p>
      <div class="actions">
        <button :disabled="saving" @click="save">{{ saving ? "Saving…" : "Save SMTP settings" }}</button>
        <button class="secondary" :disabled="testing || saving || !smtp.enabled" @click="testSmtp">{{ testing ? "Sending…" : "Send test email" }}</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="saved" class="success">SMTP settings saved.</p>
      <p v-if="testMessage" class="success">{{ testMessage }}</p>
    </template>
  </section>
</template>

<style scoped>
.section{display:flex;flex-direction:column;gap:16px}.hint{color:#999;font-size:13px;line-height:1.5}.feature-card{padding:14px 16px;border:1px solid #303030;border-radius:10px;background:#151515}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.grid label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.grid input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.toggle,.checks label{display:flex;align-items:center;gap:8px;color:#ccc;font-size:13px}.toggle input,.checks input{accent-color:#d68a34}.checks{display:flex;gap:20px}.actions{display:flex;gap:10px;flex-wrap:wrap}.section button{background:#d68a34;border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}.section button.secondary{background:#2b2b2b;color:#fff;border:1px solid #444}.section button:disabled{opacity:.6;cursor:not-allowed}.error{color:#fca5a5}.success{color:#86efac}@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style>
