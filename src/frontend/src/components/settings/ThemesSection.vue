<script setup lang="ts">
import { onMounted, ref } from "vue";
import UiModal from "../UiModal.vue";
import { useConfirm } from "../../state/dialog";
import { refreshThemes } from "../../state/themes";
import {
  fetchThemes,
  uploadTheme,
  configureTheme,
  removeTheme,
  setDefaultTheme,
  type InstalledTheme,
  type ThemeCatalogue,
} from "../../services/themes";

const catalogue = ref<ThemeCatalogue>({ default_theme: "native", themes: [] });
const busy = ref(false),
  loading = ref(true),
  dragging = ref(false);
const error = ref<string | null>(null),
  reviewError = ref<string | null>(null);
const review = ref<InstalledTheme | null>(null),
  reviewFile = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const confirm = useConfirm();
async function reload() {
  catalogue.value = await fetchThemes(true);
  await refreshThemes();
}
function message(reason: unknown) {
  return reason instanceof Error ? reason.message : "Could not update themes.";
}
async function load() {
  loading.value = true;
  error.value = null;
  try {
    await reload();
  } catch (reason) {
    error.value = message(reason);
  } finally {
    loading.value = false;
  }
}
async function mutate(action: () => Promise<unknown>) {
  busy.value = true;
  error.value = null;
  try {
    await action();
    await reload();
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
async function choose(file: File | undefined) {
  if (!file || busy.value) return;
  error.value = null;
  reviewError.value = null;
  if (!/\.utt$/i.test(file.name) || file.size > 10 * 1024 * 1024) {
    error.value = "Choose a .utt theme package smaller than 10 MiB.";
    return;
  }
  busy.value = true;
  try {
    review.value = await uploadTheme(file, true);
    reviewFile.value = file;
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
    if (fileInput.value) fileInput.value.value = "";
  }
}
function drop(event: DragEvent) {
  dragging.value = false;
  void choose(event.dataTransfer?.files[0]);
}
async function install() {
  if (!reviewFile.value || busy.value) return;
  busy.value = true;
  reviewError.value = null;
  try {
    await uploadTheme(reviewFile.value);
    await reload();
    review.value = null;
    reviewFile.value = null;
  } catch (reason) {
    reviewError.value = message(reason);
  } finally {
    busy.value = false;
  }
}
function closeReview() {
  if (busy.value) return;
  review.value = null;
  reviewFile.value = null;
  reviewError.value = null;
}
async function remove(theme: InstalledTheme) {
  if (
    await confirm({
      title: "Remove theme",
      message: `Remove ${theme.name}? People using it will return to the native interface.`,
      confirmLabel: "Remove theme",
      danger: true,
    })
  )
    await mutate(() => removeTheme(theme.id));
}
onMounted(load);
</script>

<template>
  <section class="themes-section" aria-labelledby="themes-heading">
    <div class="themes-heading">
      <div>
        <h2 id="themes-heading">Installed themes</h2>
        <p class="section-hint">
          Install CSS themes for the server. Everyone chooses their own theme in
          Appearance & interface.
        </p>
      </div>
      <button
        type="button"
        class="ui-btn ui-btn-primary"
        :disabled="busy"
        @click="fileInput?.click()"
      >
        Install theme
      </button>
    </div>
    <input
      ref="fileInput"
      class="theme-file"
      type="file"
      accept=".utt"
      aria-label="Theme package"
      @change="choose(($event.target as HTMLInputElement).files?.[0])"
    />
    <div v-if="error" class="ui-alert" role="alert">
      {{ error }}
      <button
        type="button"
        class="ui-btn ui-btn-ghost"
        :disabled="busy"
        @click="load"
      >
        Retry
      </button>
    </div>
    <div
      class="theme-install-box"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="drop"
    >
      <strong>Drop a .utt package here</strong>
      <p>Review the publisher and version before installing.</p>
      <a
        href="https://github.com/Rosefall-a/unnamed_tracking_app_themes"
        target="_blank"
        rel="noopener noreferrer"
        >Browse theme sources and CI packages</a
      >
    </div>
    <p v-if="loading" role="status">Loading installed themes…</p>
    <template v-else>
      <div class="default-theme">
        <label for="server-default-theme">Server default</label>
        <select
          id="server-default-theme"
          class="ui-field"
          :disabled="busy"
          :value="catalogue.default_theme"
          @change="
            mutate(() =>
              setDefaultTheme(($event.target as HTMLSelectElement).value),
            )
          "
        >
          <option value="native">Native interface</option>
          <option
            v-for="theme in catalogue.themes.filter((theme) => theme.enabled)"
            :key="theme.id"
            :value="theme.id"
          >
            {{ theme.name }}
          </option>
        </select>
      </div>
      <p class="section-hint">
        Used on sign-in pages and by people who select “Server default”.
      </p>
      <p v-if="!catalogue.themes.length" class="theme-empty">
        No theme packages installed yet. The native interface is available in
        light, dark and system modes.
      </p>
      <div
        v-for="kind in ['official', 'example'] as const"
        :key="kind"
        class="theme-collection"
      >
        <template v-if="catalogue.themes.some((theme) => theme.kind === kind)">
          <h3>
            {{ kind === "official" ? "Official collection" : "Examples" }}
          </h3>
          <div class="theme-grid">
            <article
              v-for="theme in catalogue.themes.filter(
                (theme) => theme.kind === kind,
              )"
              :key="theme.id"
              class="theme-card"
            >
              <div>
                <h4>{{ theme.name }}</h4>
                <span class="theme-version">v{{ theme.version }}</span>
              </div>
              <p>{{ theme.description }}</p>
              <p class="theme-publisher">
                {{ theme.publisher }} · {{ theme.supports.join(" / ") }}
              </p>
              <div class="theme-actions">
                <label
                  ><input
                    type="checkbox"
                    :checked="theme.enabled"
                    :disabled="busy"
                    @change="
                      mutate(() =>
                        configureTheme(
                          theme.id,
                          ($event.target as HTMLInputElement).checked,
                        ),
                      )
                    "
                  />
                  Enabled</label
                >
                <button
                  type="button"
                  class="ui-btn ui-btn-ghost"
                  :disabled="busy"
                  @click="remove(theme)"
                >
                  Remove
                </button>
              </div>
            </article>
          </div>
        </template>
      </div>
    </template>
    <UiModal
      v-if="review"
      title="Review theme"
      description="CSS themes change how the interface looks."
      size="wide"
      :dismissible="!busy"
      @close="closeReview"
    >
      <div class="theme-review">
        <div>
          <h3>{{ review.name }}</h3>
          <p>{{ review.description }}</p>
          <dl>
            <dt>Publisher</dt>
            <dd>{{ review.publisher }}</dd>
            <dt>Release</dt>
            <dd>v{{ review.version }}</dd>
            <dt>Collection</dt>
            <dd>{{ review.kind === "official" ? "Official" : "Example" }}</dd>
            <dt>Color modes</dt>
            <dd>{{ review.supports.join(" / ") }}</dd>
          </dl>
        </div>
        <div class="theme-review-note">
          <strong>Interface styles only</strong>
          <p>
            This package contains CSS and assets. It can restyle the sidebar,
            menus and plugin pages that use native theme tokens.
          </p>
          <p>
            There are no background workers, plugin permissions or automatic
            updates.
          </p>
          <p v-if="catalogue.themes.some((theme) => theme.id === review?.id)">
            An installed theme with this ID will be replaced. Its server default
            is retained.
          </p>
        </div>
      </div>
      <p v-if="reviewError" class="ui-alert" role="alert">{{ reviewError }}</p>
      <template #footer
        ><button
          type="button"
          class="ui-btn ui-btn-ghost"
          :disabled="busy"
          @click="closeReview"
        >
          Cancel</button
        ><button
          type="button"
          class="ui-btn ui-btn-primary"
          :disabled="busy"
          @click="install"
        >
          {{ busy ? "Installing…" : "Install theme" }}
        </button></template
      >
    </UiModal>
  </section>
</template>

<style scoped>
.themes-heading {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 20px;
  flex-wrap: wrap;
}
h2 {
  margin: 0 0 12px;
  color: var(--ui-text);
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
}
h3,
h4 {
  margin: 0 0 12px;
  color: var(--ui-text);
}
.section-hint,
.theme-card p,
.theme-review p,
.theme-install-box p {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  line-height: 1.6;
}
.theme-file {
  display: none;
}
.theme-install-box {
  padding: 26px;
  border: 1px dashed var(--ui-border);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface-2);
  margin: 20px 0 24px;
}
.theme-install-box.dragging {
  border-color: var(--ui-accent);
  background: var(--ui-accent-soft);
}
a {
  color: var(--ui-accent-text);
  overflow-wrap: anywhere;
}
.default-theme {
  display: grid;
  gap: 8px;
  max-width: 460px;
}
.theme-collection {
  margin-top: 28px;
}
.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
  gap: 18px;
}
.theme-card {
  padding: 20px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface-2);
}
.theme-card > div:first-child {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}
.theme-version,
.theme-publisher {
  color: var(--ui-faint);
  font-size: var(--ui-font-small);
}
.theme-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 20px;
}
.theme-actions label {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
}
input[type="checkbox"] {
  width: 22px;
  height: 22px;
  accent-color: var(--ui-accent);
}
.theme-empty {
  padding: 20px;
  color: var(--ui-dim);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
}
.theme-review {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 32px;
  padding: 12px 0;
}
dl {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px 20px;
  font-size: var(--ui-font-small);
}
dt {
  color: var(--ui-dim);
}
dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.theme-review-note {
  padding: 22px;
  background: var(--ui-surface-2);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  align-self: start;
}
@media (max-width: 640px) {
  .theme-review {
    grid-template-columns: minmax(0, 1fr);
    gap: 20px;
  }
  .theme-install-box {
    padding: 20px;
  }
}
</style>
