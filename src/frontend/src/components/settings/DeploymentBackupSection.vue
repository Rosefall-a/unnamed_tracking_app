<script setup lang="ts">
import { onMounted, ref } from "vue";

const password = ref("");
const confirmPassword = ref("");
const includeUsers = ref(false);
const includeSessions = ref(false);
const backupAvailable = ref(false);
const downloadEnabled = ref(false);
const loading = ref(false);
const importing = ref(false);
const message = ref<string | null>(null);
const error = ref<string | null>(null);
const selectedFile = ref<File | null>(null);

async function refreshStatus() {
  const response = await fetch("/api/settings/backup/status", { credentials: "include" });
  if (!response.ok) throw new Error("Unable to read deployment backup status.");
  const result = await response.json() as { available: boolean; download_enabled: boolean };
  backupAvailable.value = result.available;
  downloadEnabled.value = result.download_enabled;
}

function validatePassword() {
  if (password.value.length < 12) throw new Error("Backup passwords must be at least 12 characters.");
  if (password.value !== confirmPassword.value) throw new Error("The backup passwords do not match.");
}

async function exportBackup() {
  message.value = null;
  error.value = null;
  try {
    validatePassword();
    loading.value = true;
    const form = new FormData();
    form.append("password", password.value);
    form.append("include_users", String(includeUsers.value));
    form.append("include_sessions", String(includeSessions.value));
    const response = await fetch("/api/settings/backup/export", { method: "POST", credentials: "include", body: form });
    if (!response.ok) throw new Error(await response.text());
    const result = await response.json() as { saved: boolean };
    backupAvailable.value = result.saved;
    message.value = "Encrypted deployment backup saved to the server's persistent application storage.";
    password.value = "";
    confirmPassword.value = "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to export deployment backup.";
  } finally {
    loading.value = false;
  }
}

async function downloadBackup() {
  message.value = null;
  error.value = null;
  try {
    validatePassword();
    const form = new FormData();
    form.append("password", password.value);
    form.append("include_users", String(includeUsers.value));
    form.append("include_sessions", String(includeSessions.value));
    form.append("download", "true");
    const response = await fetch("/api/settings/backup/export", { method: "POST", credentials: "include", body: form });
    if (!response.ok) throw new Error(await response.text());
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "application.json";
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to download deployment backup.";
  }
}

async function importBackup() {
  if (!selectedFile.value) return;
  message.value = null;
  error.value = null;
  try {
    if (!password.value) throw new Error("Enter the backup password before importing.");
    importing.value = true;
    const form = new FormData();
    form.append("password", password.value);
    form.append("backup_file", selectedFile.value);
    const response = await fetch("/api/settings/backup/import", { method: "POST", credentials: "include", body: form });
    if (!response.ok) throw new Error(await response.text());
    message.value = "Deployment backup restored. Refresh the application if the restored settings changed your session.";
    await refreshStatus();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to import deployment backup.";
  } finally {
    importing.value = false;
  }
}

onMounted(() => { void refreshStatus().catch((err) => { error.value = err instanceof Error ? err.message : "Unable to load backup status."; }); });
</script>

<template>
  <section class="section">
    <h2>Deployment backup</h2>
    <p class="hint">Create an encrypted deployment backup that is stored in persistent application storage by default. SMTP configuration is intentionally excluded.</p>
    <p v-if="backupAvailable" class="status">A server-side application.json backup is present.</p>
    <p v-else class="hint">No server-side deployment backup has been created yet.</p>

    <label><span>Backup password</span><input v-model="password" type="password" autocomplete="new-password" /></label>
    <label><span>Confirm password</span><input v-model="confirmPassword" type="password" autocomplete="new-password" /></label>
    <label class="toggle"><input v-model="includeUsers" type="checkbox" /><span>Include users</span></label>
    <label class="toggle"><input v-model="includeSessions" :disabled="!includeUsers" type="checkbox" /><span>Include active sessions</span></label>

    <div class="actions">
      <button :disabled="loading" @click="exportBackup">{{ loading ? "Saving…" : "Save backup to server" }}</button>
      <button v-if="downloadEnabled" :disabled="loading" class="secondary" @click="downloadBackup">Download backup</button>
    </div>

    <label><span>Import backup file</span><input type="file" accept="application/json,.json" @change="selectedFile = ($event.target as HTMLInputElement).files?.[0] ?? null" /></label>
    <button class="secondary" :disabled="importing || !selectedFile" @click="importBackup">{{ importing ? "Restoring…" : "Import backup" }}</button>

    <p v-if="!downloadEnabled" class="hint">Direct deployment-secret downloads are disabled by default. Set ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD=true on the server to enable them.</p>
    <p v-if="message" class="status">{{ message }}</p>
    <p v-if="error" class="error">{{ error }}</p>
  </section>
</template>

<style scoped>
.section{display:flex;flex-direction:column;gap:14px}.section h2{margin:0;color:#fff}.hint{color:#999;font-size:13px;line-height:1.5}.section label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.section input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.toggle{flex-direction:row!important;align-items:center}.toggle input{width:16px}.actions{display:flex;gap:10px;flex-wrap:wrap}button{background:#d68a34;border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}.secondary{background:#252525;color:#ddd;border:1px solid #3a3a3a}.status{color:#86efac}.error{color:#fca5a5}button:disabled{opacity:.6}
</style>
