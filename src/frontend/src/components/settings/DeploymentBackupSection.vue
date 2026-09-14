<script setup lang="ts">
import { ref } from "vue";
import { exportDeploymentBackup } from "../../services/admin";

const password = ref("");
const confirmPassword = ref("");
const exporting = ref(false);
const error = ref<string | null>(null);
const saved = ref(false);

async function exportBackup() {
  error.value = null;
  saved.value = false;
  if (password.value.length < 12) {
    error.value = "Use a backup password of at least 12 characters.";
    return;
  }
  if (password.value !== confirmPassword.value) {
    error.value = "The backup passwords do not match.";
    return;
  }

  exporting.value = true;
  try {
    const blob = await exportDeploymentBackup(password.value);
    const url = URL.createObjectURL(blob);
    const date = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const link = document.createElement("a");
    link.href = url;
    link.download = `archive-deployment-backup-${date}.json`;
    link.click();
    URL.revokeObjectURL(url);
    password.value = "";
    confirmPassword.value = "";
    saved.value = true;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to export deployment backup.";
  } finally {
    exporting.value = false;
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Deployment backup</h2>
    <p class="section-hint">
      Export the server's deployment settings, provider credentials, SMTP/OIDC
      secrets, and persistent Fernet keys without exporting users, sessions,
      libraries, media, or other user data. The backup is encrypted before it
      leaves the server.
    </p>

    <div class="warning">
      <strong>Protect this file.</strong> It contains the keys needed to decrypt
      deployment secrets. Store it like a password vault backup and keep the
      backup password separate from the file.
    </div>

    <form class="backup-form" @submit.prevent="exportBackup">
      <label class="field">
        <span>Backup password</span>
        <input
          v-model="password"
          type="password"
          minlength="12"
          maxlength="256"
          autocomplete="new-password"
          placeholder="At least 12 characters"
          required
        />
      </label>
      <label class="field">
        <span>Confirm backup password</span>
        <input
          v-model="confirmPassword"
          type="password"
          minlength="12"
          maxlength="256"
          autocomplete="new-password"
          required
        />
      </label>
      <p v-if="error" class="form-error">{{ error }}</p>
      <p v-if="saved" class="form-success">Encrypted deployment backup downloaded.</p>
      <button type="submit" class="primary-button" :disabled="exporting">
        {{ exporting ? "Encrypting…" : "Export encrypted deployment backup" }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.settings-section h2{margin:0 0 8px;padding-left:12px;border-left:3px solid #d68a34;font-size:1rem;color:#fff}.section-hint{color:#999;font-size:.82rem;line-height:1.6;margin:0 0 18px}.warning{background:rgba(214,138,52,.08);border:1px solid rgba(214,138,52,.28);border-radius:9px;padding:12px 14px;color:#c9c9c9;font-size:.8rem;line-height:1.5;margin-bottom:18px}.warning strong{color:#d68a34}.backup-form{display:flex;flex-direction:column;gap:14px;max-width:560px}.field{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:.82rem}.field input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px 12px;font:inherit}.field input:focus{outline:none;border-color:#d68a34}.primary-button{align-self:flex-start;background:#d68a34;color:#111;border:none;border-radius:8px;padding:11px 16px;font-weight:600;cursor:pointer}.primary-button:disabled{opacity:.6;cursor:not-allowed}.form-error{color:#fca5a5;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);border-radius:8px;padding:8px 10px;font-size:13px}.form-success{color:#86efac;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);border-radius:8px;padding:8px 10px;font-size:13px}
</style>
