<script setup lang="ts">
import { onMounted, ref } from "vue";
import AppBrand from "../AppBrand.vue";
import {
  branding,
  brandingError,
  brandingLoaded,
  loadBranding,
  applyBranding,
} from "../../state/branding";
import {
  saveBrandingName,
  uploadBrandingAsset,
  removeBrandingAsset,
  type Branding,
  type BrandingAsset,
} from "../../services/branding";

const name = ref(branding.value.app_name);
const saving = ref(false);
const error = ref<string | null>(null);
const saved = ref(false);
const loading = ref(true);
async function initialize() {
  loading.value = true;
  await loadBranding();
  if (!brandingError.value) name.value = branding.value.app_name;
  loading.value = false;
}
onMounted(initialize);

async function save(operation: () => Promise<Branding>) {
  saving.value = true;
  saved.value = false;
  error.value = null;
  try {
    applyBranding(await operation());
    saved.value = true;
  } catch (reason) {
    error.value =
      reason instanceof Error ? reason.message : "Could not save branding.";
  } finally {
    saving.value = false;
  }
}

async function upload(kind: BrandingAsset, event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) {
    error.value = "Choose an image no larger than 2 MB.";
    saved.value = false;
  } else {
    await save(() => uploadBrandingAsset(kind, file));
  }
  input.value = "";
}
</script>

<template>
  <section class="branding-section" aria-labelledby="branding-heading">
    <h2 id="branding-heading">App identity</h2>
    <p class="section-hint">
      The name, logo and browser icon apply to everyone on this server,
      including the sign-in page.
    </p>
    <div v-if="brandingError" class="ui-alert" role="alert">
      {{ brandingError }}
      <button
        type="button"
        class="ui-btn ui-btn-ghost"
        :disabled="loading"
        @click="initialize"
      >
        Retry
      </button>
    </div>
    <div class="branding-preview"><AppBrand /></div>
    <form @submit.prevent="save(() => saveBrandingName(name.trim()))">
      <fieldset
        :disabled="saving || loading || !brandingLoaded || !!brandingError"
      >
        <div class="branding-name">
          <label for="branding-name">Application name</label>
          <div class="branding-name-controls">
            <input
              id="branding-name"
              v-model="name"
              class="ui-field"
              required
              maxlength="64"
              autocomplete="off"
            />
            <button
              type="submit"
              class="ui-btn ui-btn-primary"
              :disabled="!name.trim()"
            >
              Save name
            </button>
          </div>
        </div>
        <div
          v-for="kind in ['logo', 'favicon'] as const"
          :key="kind"
          class="branding-asset"
        >
          <div>
            <label :for="`branding-${kind}`">{{
              kind === "logo" ? "App logo" : "Browser icon"
            }}</label>
            <p>
              {{
                kind === "logo"
                  ? "Shown in navigation and on sign-in and setup pages."
                  : "Used in browser tabs. Your app logo is the fallback."
              }}
            </p>
          </div>
          <img
            v-if="kind === 'favicon' || branding.logo_url"
            :src="kind === 'logo' ? branding.logo_url! : branding.favicon_url"
            alt=""
            class="asset-preview"
          />
          <input
            :id="`branding-${kind}`"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            @change="upload(kind, $event)"
          />
          <button
            v-if="
              kind === 'logo'
                ? !!branding.logo_url
                : branding.favicon_url.includes('/assets/favicon/')
            "
            type="button"
            class="ui-btn ui-btn-ghost"
            @click="save(() => removeBrandingAsset(kind))"
          >
            Remove {{ kind === "logo" ? "logo" : "browser icon" }}
          </button>
        </div>
      </fieldset>
    </form>
    <p class="section-hint">
      Upload a static PNG, JPEG or WebP up to 2 MB and 4096 pixels per side (16
      megapixels). Images are resized to fit 512 pixels and saved without
      metadata.
    </p>
    <p v-if="saving" role="status">Saving branding…</p>
    <p v-else-if="saved" role="status" class="branding-saved">
      Branding saved.
    </p>
    <p v-if="error" role="alert" class="ui-alert">{{ error }}</p>
    <p class="section-hint">
      For your own theme and completed-game badges, open
      <RouterLink to="/settings?section=appearance">Appearance</RouterLink>.
    </p>
  </section>
</template>

<style scoped>
.branding-section {
  display: grid;
  gap: 20px;
}
h2 {
  margin: 0;
  font-size: var(--ui-font-heading);
  font-weight: 650;
}
.section-hint,
.branding-asset p {
  color: var(--ui-dim);
  font-size: 13px;
  line-height: 1.6;
}
.branding-preview {
  padding: 24px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface-2);
}
fieldset {
  display: grid;
  gap: 24px;
  border: 0;
  padding: 0;
  margin: 0;
  min-width: 0;
}
label {
  display: block;
  font-weight: 600;
}
.branding-name-controls {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}
.branding-name-controls input {
  min-width: 0;
  flex: 1;
}
.branding-asset {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding-top: 24px;
  border-top: 1px solid var(--ui-border);
}
.branding-asset input,
.branding-asset button {
  grid-column: 1 / -1;
  max-width: 100%;
  min-height: var(--ui-control-height);
}
.branding-asset input::file-selector-button {
  font: inherit;
  color: var(--ui-text);
  background: var(--ui-surface-2);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  min-height: var(--ui-control-height);
  padding: 8px 14px;
  margin-right: 12px;
  cursor: pointer;
}
.asset-preview {
  width: 48px;
  height: 48px;
  object-fit: contain;
  border-radius: 12px;
  background: var(--ui-surface-2);
}
.branding-saved {
  color: var(--ui-good);
}
@media (max-width: 760px) {
  .branding-name-controls {
    flex-direction: column;
  }
}
</style>
