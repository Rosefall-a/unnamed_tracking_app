<script setup lang="ts">
import { ref } from "vue";
import { exportDeploymentBackup } from "../../services/exportImport";

const exportPassword = ref("");
const exportConfirmPassword = ref("");
const includeUsers = ref(false);
const includeSessions = ref(false);
const fullInstallation = ref(false);
const saveToSetupPath = ref(false);
const exporting = ref(false);
const error = ref<string | null>(null);
const message = ref<string | null>(null);

function validateExport() {
  if (exportPassword.value.length < 12) throw new Error("Backup passwords must be at least 12 characters.");
  if (exportConfirmPassword.value !== exportPassword.value) throw new Error("The backup passwords do not match.");
}

async function exportBackup() {
  error.value = null;
  message.value = null;
  try {
    validateExport();
    exporting.value = true;
    const blob = await exportDeploymentBackup({
      password: exportPassword.value,
      include_users: fullInstallation.value || includeUsers.value,
      include_sessions: fullInstallation.value || includeSessions.value,
      full_installation: fullInstallation.value,
      save_to_setup_path: saveToSetupPath.value,
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fullInstallation.value ? "application-full-backup.json" : "application.json";
    link.click();
    URL.revokeObjectURL(url);
    exportPassword.value = "";
    exportConfirmPassword.value = "";
    message.value = "Encrypted deployment backup created. Keep the backup and its password separate.";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to export deployment backup.";
  } finally {
    exporting.value = false;
  }
}


</script>

<template>
  <section class="section">
    <h2>Deployment backup</h2>
    <p class="hint">Create password-protected deployment configuration for use during first-run setup or automated environment bootstrap. This includes application/provider settings, SMTP/OIDC configuration, and the persistent encryption key. User accounts and active sessions are optional.</p>

    <div class="warning"><strong>Protect this file.</strong> The archive contains deployment secrets. Keep its password separate from the file.</div>

    <div class="panel">
      <h3>Export</h3>
      <form class="form" @submit.prevent="exportBackup">
        <label><span>Backup password</span><input v-model="exportPassword" type="password" minlength="12" maxlength="256" autocomplete="new-password" placeholder="At least 12 characters" required /></label>
        <label><span>Confirm backup password</span><input v-model="exportConfirmPassword" type="password" minlength="12" maxlength="256" autocomplete="new-password" required /></label>
        <label class="check"><input v-model="includeUsers" type="checkbox" :disabled="fullInstallation" /><span>Include users and API keys</span></label>
        <label class="check"><input v-model="includeSessions" type="checkbox" :disabled="fullInstallation || !includeUsers" /><span>Include active sessions</span></label>
        <label class="check"><input v-model="fullInstallation" type="checkbox" /><span>Full installation (users + active sessions)</span></label>
        <label class="check"><input v-model="saveToSetupPath" type="checkbox" /><span>Also save to the configured setup path</span></label>
        <p class="hint">The setup path is APPLICATION_JSON_PATH, defaulting to /data/application.json. Saving it there makes clearing and recreating a test deployment repeatable.</p>
        <button type="submit" class="primary" :disabled="exporting">{{ exporting ? "Encrypting…" : "Export encrypted deployment backup" }}</button>
      </form>
    </div>


    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="message" class="success">{{ message }}</div>

  </section>
</template>

<style scoped>
.section{display:flex;flex-direction:column;gap:16px}.section h2{margin:0;color:#fff}.hint{color:#999;font-size:13px;line-height:1.5}.warning{background:rgba(214,138,52,.08);border:1px solid rgba(214,138,52,.28);border-radius:9px;padding:12px 14px;color:#c9c9c9;font-size:.8rem;line-height:1.5}.warning strong{color:#d68a34}.panel{border:1px solid #2f2f2f;border-radius:10px;padding:18px;background:#151515}.panel h3{margin:0 0 12px;color:#fff}.form{display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:end;max-width:760px}.form label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.form input,.modal input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.check{flex-direction:row!important;align-items:center;gap:8px!important}.check input{accent-color:#d68a34}.form>.hint{grid-column:1/-1;margin:0}.primary,.secondary{border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}.primary{background:#d68a34;color:#111}.secondary{background:rgba(255,255,255,.08);color:#fff}.primary:disabled,.secondary:disabled{opacity:.6;cursor:not-allowed}.error{color:#fca5a5;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);border-radius:8px;padding:8px 10px}.success{color:#86efac;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);border-radius:8px;padding:8px 10px}.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:20px;z-index:100}.modal{width:min(460px,100%);background:#1a1a1a;border:1px solid #363636;border-radius:12px;padding:22px;box-shadow:0 24px 64px rgba(0,0,0,.65);display:flex;flex-direction:column;gap:14px}.modal h3{margin:0;color:#fff}.modal p{margin:0;color:#999;font-size:.85rem;line-height:1.5}.modal label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.modal-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:4px}@media(max-width:760px){.form{grid-template-columns:1fr}}
</style>
