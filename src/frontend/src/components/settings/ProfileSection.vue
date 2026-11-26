<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import PasswordInput from "../PasswordInput.vue";
import { currentUser, checkAuth } from "../../state/auth";
import PasswordRequirements from "./PasswordRequirements.vue";
import SettingsCard from "./SettingsCard.vue";
import {
  fetchPasswordPolicy,
  passwordValidationErrors,
  type PasswordPolicy,
} from "../../services/passwordPolicy";
import {
  updateProfile,
  uploadProfilePicture,
  profilePictureSrc,
} from "../../services/auth";

const isMock = computed(() => currentUser.value?.id === "mock");

const avatarUrl = computed(() => profilePictureSrc(currentUser.value));
const avatarFailed = ref(false);
watch(avatarUrl, () => (avatarFailed.value = false));

const username = ref("");
const email = ref("");
// filled (and refilled after a save) from the signed-in user rather than
// captured once at setup, so the fields are never blank if this mounts
// before the account has finished loading
watch(
  currentUser,
  (u) => {
    if (!u) return;
    username.value = u.username;
    email.value = u.email;
  },
  { immediate: true },
);
const currentPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const saving = ref(false);
const saveError = ref<string | null>(null);
const saveSuccess = ref(false);
const passwordPolicy = ref<PasswordPolicy | null>(null);

// otherwise "Saved" keeps showing after a successful save even
// once the user starts typing something new, reading as if the in-progress
// edit was already saved. Only username/email, not the password fields,
// saveProfile() itself clears those right after a successful save, and
// watching them here would stomp saveSuccess back to false in that same tick.
watch([username, email], () => {
  saveSuccess.value = false;
});

onMounted(async () => {
  try {
    passwordPolicy.value = await fetchPasswordPolicy();
  } catch (err) {
    saveError.value =
      err instanceof Error ? err.message : "Could not load password policy";
  }
});

const uploading = ref(false);
const uploadError = ref<string | null>(null);

async function saveProfile() {
  saving.value = true;
  saveError.value = null;
  saveSuccess.value = false;
  try {
    await updateProfile({
      username: username.value.trim() || undefined,
      email: email.value.trim() || undefined,
    });
    await checkAuth();
    saveSuccess.value = true;
  } catch (err) {
    saveError.value =
      err instanceof Error ? err.message : "Could not update profile";
  } finally {
    saving.value = false;
  }
}

// The password has its own card and button, so changing your name never asks
// about your password and a typo in one never blocks saving the other.
const savingPassword = ref(false);
const passwordError = ref<string | null>(null);
const passwordSaved = ref(false);
watch([currentPassword, newPassword, confirmPassword], () => {
  if (newPassword.value || currentPassword.value) passwordSaved.value = false;
});

async function savePassword() {
  passwordError.value = null;
  if (!newPassword.value) {
    passwordError.value = "Type a new password.";
    return;
  }
  const validationErrors = passwordPolicy.value
    ? passwordValidationErrors(newPassword.value, passwordPolicy.value)
    : ["Password requirements could not be loaded."];
  if (validationErrors.length) {
    passwordError.value = validationErrors[0];
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = "The new passwords do not match.";
    return;
  }
  if (!currentPassword.value) {
    passwordError.value = "Enter your current password to set a new one.";
    return;
  }
  savingPassword.value = true;
  try {
    await updateProfile({
      currentPassword: currentPassword.value,
      newPassword: newPassword.value,
    });
    currentPassword.value = "";
    newPassword.value = "";
    confirmPassword.value = "";
    passwordSaved.value = true;
  } catch (err) {
    passwordError.value =
      err instanceof Error ? err.message : "Could not change password";
  } finally {
    savingPassword.value = false;
  }
}

async function onAvatarFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file || !currentUser.value) return;

  uploading.value = true;
  uploadError.value = null;

  try {
    const version = await uploadProfilePicture(currentUser.value.id, file);
    // changed in place, so every avatar picks up the new address without the
    // username/email fields being refilled over unsaved edits
    currentUser.value.profile_picture_version = version;
  } catch (err) {
    uploadError.value =
      err instanceof Error ? err.message : "Could not upload picture";
  } finally {
    uploading.value = false;
    // without this, re-picking the same file after a failed upload fires
    // no 'change' event at all (the input's value never actually changed)
    input.value = "";
  }
}
</script>

<template>
  <SettingsCard
    title="Profile"
    description="How you appear to other people on this server."
  >
    <div class="avatar-row">
      <img
        v-if="!isMock && avatarUrl && !avatarFailed"
        :src="avatarUrl"
        alt=""
        class="avatar-image"
        @error="avatarFailed = true"
      />
      <div v-else class="avatar-fallback">
        {{ (currentUser?.username ?? "?").slice(0, 2).toUpperCase() }}
      </div>
      <div class="avatar-meta">
        <strong>{{ currentUser?.username }}</strong>
        <span class="st-muted">{{
          currentUser?.is_admin ? "Admin" : "Member"
        }}</span>
      </div>
      <label v-if="!isMock" class="st-btn upload-btn">
        <input
          type="file"
          accept="image/*"
          hidden
          @change="onAvatarFileChange"
        />
        {{ uploading ? "Uploading…" : "Change picture" }}
      </label>
      <p v-else class="st-muted mock-note">
        Profile pictures aren't available in mock mode.
      </p>
    </div>
    <p v-if="uploadError" class="st-error">{{ uploadError }}</p>

    <form @submit.prevent="saveProfile">
      <label class="st-flabel" for="profile-username">Username</label>
      <input
        id="profile-username"
        v-model="username"
        class="st-field"
        type="text"
        autocomplete="username"
      />
      <label class="st-flabel" for="profile-email">Email</label>
      <input
        id="profile-email"
        v-model="email"
        class="st-field"
        type="email"
        autocomplete="email"
      />
      <p v-if="saveError" class="st-error">{{ saveError }}</p>
      <div class="st-btns form-actions">
        <button type="submit" class="st-btn primary" :disabled="saving">
          {{ saving ? "Saving…" : "Save profile" }}
        </button>
        <span v-if="saveSuccess" class="saved">Saved</span>
      </div>
    </form>
  </SettingsCard>

  <SettingsCard
    title="Password"
    description="Its own box, so changing your name never asks about your password."
  >
    <form @submit.prevent="savePassword">
      <label class="st-flabel">Current password</label>
      <PasswordInput
        v-model="currentPassword"
        mode="new"
        autocomplete="current-password"
      />
      <label class="st-flabel">New password</label>
      <PasswordInput
        v-model="newPassword"
        mode="new"
        autocomplete="new-password"
      />
      <PasswordRequirements
        v-if="newPassword && passwordPolicy"
        :password="newPassword"
        :policy="passwordPolicy"
      />
      <template v-if="newPassword">
        <label class="st-flabel">Confirm new password</label>
        <PasswordInput
          v-model="confirmPassword"
          mode="new"
          autocomplete="new-password"
        />
      </template>
      <p v-if="passwordError" class="st-error">{{ passwordError }}</p>
      <div class="st-btns form-actions">
        <button type="submit" class="st-btn" :disabled="savingPassword">
          {{ savingPassword ? "Changing…" : "Change password" }}
        </button>
        <span v-if="passwordSaved" class="saved">Password changed</span>
      </div>
    </form>
  </SettingsCard>
</template>

<style scoped>
.avatar-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0 6px;
}
.avatar-image,
.avatar-fallback {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}
.avatar-fallback {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
}
.avatar-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.avatar-meta strong {
  color: var(--ui-heading);
}
.upload-btn {
  margin-left: auto;
}
.mock-note {
  margin: 0 0 0 auto;
}
.form-actions {
  align-items: center;
  margin-top: 14px;
}
.saved {
  color: var(--ui-good-text);
  font-size: 12.5px;
}
</style>
