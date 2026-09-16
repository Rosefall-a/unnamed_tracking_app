<script setup lang="ts">
import { ref } from "vue";
import { currentUser } from "../../state/auth";
import { logout } from "../../services/auth";
import { exportDeploymentBackup, inspectDeploymentBackup, restoreDeploymentBackup } from "../../services/exportImport";
import type { DeploymentBackupPreview } from "../../services/exportImport";

const exportPassword = ref("");
const exportConfirmPassword = ref("");
const restorePassword = ref("");
const file = ref<File | null>(null);
const preview = ref<DeploymentBackupPreview | null>(null);
const selected = ref<string[]>([]);
const exporting = ref(false);
const processing = ref(false);
const error = ref<string | null>(null);
const message = ref<string | null>(null);
const sessionsRevoked = ref(false);
const showRestorePasswordModal = ref(false);
const showEncryptionConfirmModal = ref(false);

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
    const blob = await exportDeploymentBackup(exportPassword.value);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `archive-deployment-backup-${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}.json`;
    link.click();
    URL.revokeObjectURL(url);
    exportPassword.value = "";
    exportConfirmPassword.value = "";
    message.value = "Encrypted deployment backup downloaded. Keep the backup and its password separate.";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to export deployment backup.";
  } finally {
    exporting.value = false;
  }
}

function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement;
  file.value = input.files?.[0] ?? null;
  preview.value = null;
  selected.value = [];
  restorePassword.value = "";
  showRestorePasswordModal.value = false;
  error.value = null;
  message.value = null;
}

function openRestorePasswordModal() {
  error.value = null;
  if (!file.value) {
    error.value = "Choose an encrypted deployment backup first.";
    return;
  }
  restorePassword.value = "";
  showRestorePasswordModal.value = true;
}

async function decryptBackup() {
  error.value = null;
  message.value = null;
  if (!file.value) {
    error.value = "Choose an encrypted deployment backup first.";
    return;
  }
  if (restorePassword.value.length < 12) {
    error.value = "Enter the backup password (at least 12 characters).";
    return;
  }
  processing.value = true;
  try {
    preview.value = await inspectDeploymentBackup(file.value, restorePassword.value);
    selected.value = preview.value.sections.filter((section) => section.available).map((section) => section.id);
    showRestorePasswordModal.value = false;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to decrypt deployment backup.";
  } finally {
    processing.value = false;
  }
}

function requestRestore() {
  error.value = null;
  if (selected.value.includes("encryption")) {
    showEncryptionConfirmModal.value = true;
    return;
  }
  void performRestore();
}

async function performRestore() {
  showEncryptionConfirmModal.value = false;
  error.value = null;
  message.value = null;
  sessionsRevoked.value = false;
  if (!file.value || !selected.value.length) {
    error.value = "Choose the backup and at least one section to restore.";
    return;
  }
  processing.value = true;
  try {
    const result = await restoreDeploymentBackup(file.value, restorePassword.value, selected.value);
    message.value = result.message;
    sessionsRevoked.value = result.sessions_revoked;
    preview.value = null;
    if (result.sessions_revoked) restorePassword.value = "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to restore deployment backup.";
  } finally {
    processing.value = false;
  }
}

async function signOutNow() {
  currentUser.value = null;
  try {
    await logout();
  } catch (err) {
    void err;
  }
  window.location.assign("/login");
}

function refreshPage() {
  window.location.reload();
}
</script>
<template>
  <section class="section">
    <h2>Deployment backup</h2>
    <p class="hint">Export or restore deployment settings, provider credentials, SMTP/OIDC secrets, and persistent Fernet keys. Users, sessions, libraries, media and other user data are never included.</p>
    <div class="warning"><strong>Protect this file.</strong> The archive contains deployment secrets. Keep its password separate from the file.</div>
    <div class="panel">
      <h3>Export</h3>
      <form class="form" @submit.prevent="exportBackup">
        <label><span>Backup password</span><input v-model="exportPassword" type="password" minlength="12" maxlength="256" autocomplete="new-password" placeholder="At least 12 characters" required /></label>
        <label><span>Confirm backup password</span><input v-model="exportConfirmPassword" type="password" minlength="12" maxlength="256" autocomplete="new-password" required /></label>
        <button type="submit" class="primary" :disabled="exporting">{{ exporting ? "Encrypting…" : "Export encrypted deployment backup" }}</button>
      </form>
    </div>
    <div class="panel">
      <h3>Restore</h3>
      <p class="hint">Upload the encrypted backup first. The password is requested in a secure in-app dialog and is kept separate from the export password.</p>
      <label class="upload"><span>{{ file ? file.name : "Choose encrypted backup…" }}</span><input type="file" accept="application/json" @change="onFileSelected" /></label>
      <div v-if="file" class="restore-file">
        <span>Ready to decrypt <strong>{{ file.name }}</strong></span>
        <button v-if="!preview" type="button" class="secondary" :disabled="processing" @click="openRestorePasswordModal">{{ processing ? "Decrypting…" : "Enter password and review" }}</button>
      </div>
      <div v-if="preview" class="restore-options">
        <h4>Choose what to replace</h4>
        <label v-for="section in preview.sections" :key="section.id" class="option"><input v-model="selected" type="checkbox" :value="section.id" :disabled="!section.available" /><span><strong>{{ section.label }}</strong><small>{{ section.description }}</small></span></label>
        <button type="button" class="primary" :disabled="processing || !selected.length" @click="requestRestore">{{ processing ? "Restoring…" : "Restore selected settings" }}</button>
      </div>
    </div>
    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="message" class="success">{{ message }}</div>
    <div v-if="sessionsRevoked" class="session-warning"><strong>Your session was invalidated.</strong><p>The restore completed, but the server revoked active sessions because encryption keys were replaced. Nothing signed you out automatically.</p><div><button type="button" class="primary" @click="signOutNow">Sign out now</button><button type="button" class="secondary" @click="refreshPage">Refresh page</button></div></div>
    <div class="hint"><strong>Restore scope:</strong> this is a configuration/secret migration artifact, not a complete application backup. Keep your normal PostgreSQL and <code>/data</code> backups as well.</div>

    <div v-if="showRestorePasswordModal" class="modal-backdrop" @click.self="showRestorePasswordModal = false">
      <form class="modal" @submit.prevent="decryptBackup">
        <h3>Decrypt deployment backup</h3>
        <p>Enter the password used when this backup was exported. Nothing will be changed until you review and confirm the restore sections.</p>
        <label><span>Backup password</span><input v-model="restorePassword" type="password" minlength="12" maxlength="256" autocomplete="current-password" placeholder="At least 12 characters" autofocus required /></label>
        <div class="modal-actions"><button type="button" class="secondary" :disabled="processing" @click="showRestorePasswordModal = false">Cancel</button><button type="submit" class="primary" :disabled="processing">{{ processing ? "Decrypting…" : "Decrypt and review" }}</button></div>
      </form>
    </div>
    <div v-if="showEncryptionConfirmModal" class="modal-backdrop" @click.self="showEncryptionConfirmModal = false">
      <div class="modal">
        <h3>Replace encryption keys?</h3>
        <p>Restoring encryption keys also restores the encrypted deployment settings that belong to those keys and invalidates all active sessions. You will need to sign in again after the restore.</p>
        <div class="modal-actions"><button type="button" class="secondary" @click="showEncryptionConfirmModal = false">Cancel</button><button type="button" class="danger" :disabled="processing" @click="performRestore">Restore and invalidate sessions</button></div>
      </div>
    </div>
  </section>
</template>
<style scoped>
.section{display:flex;flex-direction:column;gap:16px}.section h2{margin:0;color:#fff}.hint{color:#999;font-size:13px;line-height:1.5}.warning{background:rgba(214,138,52,.08);border:1px solid rgba(214,138,52,.28);border-radius:9px;padding:12px 14px;color:#c9c9c9;font-size:.8rem;line-height:1.5}.warning strong{color:#d68a34}.panel{border:1px solid #2f2f2f;border-radius:10px;padding:18px;background:#151515}.panel h3{margin:0 0 12px;color:#fff}.form{display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:end;max-width:760px}.form label,.panel>label,.modal label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.form input,.panel input,.modal input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.primary,.secondary,.danger{border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}.primary{background:#d68a34;color:#111}.secondary{background:rgba(255,255,255,.08);color:#fff}.danger{background:rgba(220,38,38,.2);color:#fca5a5}.primary:disabled,.secondary:disabled,.danger:disabled{opacity:.6;cursor:not-allowed}.upload{display:inline-flex!important;width:max-content;background:rgba(255,255,255,.08);padding:10px 14px;border-radius:8px;cursor:pointer;margin-bottom:12px}.upload input{display:none}.restore-file{display:flex;align-items:center;justify-content:space-between;gap:12px;border:1px solid #333;border-radius:8px;background:#111;padding:12px;color:#ccc}.restore-options{margin-top:16px;border-top:1px solid #2a2a2a;padding-top:16px}.restore-options h4{margin:0 0 10px;color:#fff}.option{display:flex;gap:10px;align-items:flex-start;padding:11px;border:1px solid #333;border-radius:8px;background:#111;margin-bottom:8px;cursor:pointer}.option input{margin-top:3px}.option span{display:flex;flex-direction:column;gap:3px}.option small{color:#888;line-height:1.4}.error{color:#fca5a5;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);border-radius:8px;padding:8px 10px}.success{color:#86efac;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);border-radius:8px;padding:8px 10px}.session-warning{background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.35);border-radius:10px;padding:14px;color:#fca5a5}.session-warning strong{color:#fff}.session-warning p{margin:6px 0 12px;line-height:1.5}.session-warning button+button{margin-left:8px}.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:20px;z-index:100}.modal{width:min(460px,100%);background:#1a1a1a;border:1px solid #363636;border-radius:12px;padding:22px;box-shadow:0 24px 64px rgba(0,0,0,.65);display:flex;flex-direction:column;gap:14px}.modal h3{margin:0;color:#fff}.modal p{margin:0;color:#999;font-size:.85rem;line-height:1.5}.modal-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:4px}code{color:#ddd}@media(max-width:760px){.form{grid-template-columns:1fr}.restore-file{align-items:stretch;flex-direction:column}}
</style>