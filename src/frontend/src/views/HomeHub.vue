<script setup lang="ts">
import { computed, ref, watch } from "vue";
import PageHeader from "../components/PageHeader.vue";
import AccountChip from "../components/AccountChip.vue";
import HomeWidgetPicker from "../components/HomeWidgetPicker.vue";
import HomeCoreWidget from "../components/HomeCoreWidget.vue";
import UiModal from "../components/UiModal.vue";
import PluginExtensionSlot from "../components/plugins/PluginExtensionSlot.vue";
import PluginHomeWidget from "../components/plugins/PluginHomeWidget.vue";
import PluginWidgetConfiguration from "../components/plugins/PluginWidgetConfiguration.vue";
import type { PluginSlotContribution } from "../state/pluginExtensions";
import type { UiValues } from "../services/pluginUi";
import GameFormModal from "../components/GameFormModal.vue";
import CollectionPickerModal from "../components/CollectionPickerModal.vue";
import RandomGamePicker from "../components/RandomGamePicker.vue";
import { pluginSlots } from "../state/pluginExtensions";
import { currentUser } from "../state/auth";
import {
  preferences,
  preferencesLoaded,
  preferencesError,
  loadSharedPreferences,
} from "../state/preferences";
import { queuePreferences } from "../services/preferences";
import {
  CORE_HOME_WIDGETS,
  selectedHomeWidgets,
} from "../services/homeWidgets";
import { fetchGames, deleteGame } from "../services/games";
import { fetchWeeklyDigest, type WeeklyDigest } from "../services/stats";
import type { Game } from "../types/game";

const hasHomeOverride = computed(() =>
  pluginSlots.value.some((item) => item.slot === "home.replace"),
);
const replacementFailed = ref(false);
watch(
  () => pluginSlots.value,
  () => {
    replacementFailed.value = false;
  },
);
const pluginWidgets = computed(() =>
  pluginSlots.value.filter(
    (item) =>
      item.slot === "home.after-widgets" &&
      (!item.widget?.visibility.admin_only || currentUser.value?.is_admin),
  ),
);
const games = ref<Game[]>([]);
const digest = ref<WeeklyDigest | null>(null);
const gamesLoading = ref(false);
const digestLoading = ref(false);
const gamesError = ref<string | null>(null);
const digestError = ref<string | null>(null);
let gamesLoaded = false;
let digestLoaded = false;
let dataGeneration = 0;
let gamesRequest = 0;
let digestRequest = 0;
const collections = computed(() =>
  [...new Set(games.value.flatMap((game) => game.collections))].sort((a, b) =>
    a.localeCompare(b),
  ),
);
const choices = computed(() => [
  ...CORE_HOME_WIDGETS,
  ...collections.value.map((name) => ({
    id: `collection:${name}`,
    title: name,
    description: "A shelf from your game collection.",
  })),
  ...pluginWidgets.value.map((item) => ({
    id: `plugin:${item.pluginId}:${item.extensionId}`,
    title: item.widget?.title ?? item.page.title,
    description: item.widget?.description || `From ${item.pluginId}`,
  })),
]);
const selected = computed(() =>
  selectedHomeWidgets(preferences.value.home_widgets, choices.value),
);
const showPicker = ref(false);
const saving = ref(false);
const saveError = ref<string | null>(null);
const saved = ref(false);
const configuring = ref<PluginSlotContribution | null>(null);
const configuringBusy = ref(false);
const configurationError = ref<string | null>(null);
watch(
  () => currentUser.value?.id,
  () => {
    configuring.value = null;
  },
);
watch(pluginWidgets, (widgets) => {
  if (
    configuring.value &&
    !widgets.some(
      (item) =>
        item.pluginId === configuring.value?.pluginId &&
        item.extensionId === configuring.value?.extensionId,
    )
  )
    configuring.value = null;
});
const showTour = ref(false);
const editingGame = ref<Game | null>(null);
const showForm = ref(false);
const collectionGame = ref<Game | null>(null);
const showRandom = ref(false);
const deletingGame = ref<Game | null>(null);
const deleting = ref(false);
const deleteError = ref<string | null>(null);

async function loadGames() {
  const generation = dataGeneration;
  const request = ++gamesRequest;
  gamesLoading.value = true;
  gamesError.value = null;
  try {
    const result = await fetchGames();
    if (generation !== dataGeneration || request !== gamesRequest) return;
    games.value = result;
    gamesLoaded = true;
  } catch (reason) {
    if (generation === dataGeneration && request === gamesRequest)
      gamesError.value =
        reason instanceof Error ? reason.message : "Could not load your games.";
  } finally {
    if (generation === dataGeneration && request === gamesRequest)
      gamesLoading.value = false;
  }
}
async function loadDigest() {
  const generation = dataGeneration;
  const request = ++digestRequest;
  digestLoading.value = true;
  digestError.value = null;
  try {
    const result = await fetchWeeklyDigest();
    if (generation !== dataGeneration || request !== digestRequest) return;
    digest.value = result;
    digestLoaded = true;
  } catch (reason) {
    if (generation === dataGeneration && request === digestRequest)
      digestError.value =
        reason instanceof Error
          ? reason.message
          : "Could not load this week's activity.";
  } finally {
    if (generation === dataGeneration && request === digestRequest)
      digestLoading.value = false;
  }
}
function usesGames(id: string) {
  return !id.startsWith("plugin:") && !["goals", "weekly-digest"].includes(id);
}
function ensureData() {
  if (
    !preferencesLoaded.value ||
    preferencesError.value ||
    (hasHomeOverride.value && !replacementFailed.value)
  )
    return;
  const ids = preferences.value.home_widgets;
  if (
    (showPicker.value || ids.some(usesGames)) &&
    !gamesLoaded &&
    !gamesLoading.value &&
    !gamesError.value
  )
    void loadGames();
  if (
    ids.includes("weekly-digest") &&
    !digestLoaded &&
    !digestLoading.value &&
    !digestError.value
  )
    void loadDigest();
}
watch(
  () => currentUser.value?.id,
  () => {
    dataGeneration++;
    games.value = [];
    digest.value = null;
    gamesLoaded = digestLoaded = false;
    gamesLoading.value = digestLoading.value = false;
    gamesError.value = digestError.value = null;
    showPicker.value =
      showTour.value =
      showForm.value =
      showRandom.value =
        false;
    editingGame.value = collectionGame.value = deletingGame.value = null;
  },
);
watch(
  [
    () => preferences.value.home_widgets,
    preferencesLoaded,
    preferencesError,
    showPicker,
    hasHomeOverride,
    replacementFailed,
  ],
  ensureData,
  { immediate: true },
);
function widgetError(id: string) {
  if (usesGames(id) && gamesError.value) return gamesError.value;
  if (id === "weekly-digest") return digestError.value;
  return null;
}
function widgetLoading(id: string) {
  return (
    (usesGames(id) && !gamesLoaded && !gamesError.value) ||
    (id === "weekly-digest" && !digestLoaded && !digestError.value)
  );
}
function retryWidget(id: string) {
  if (usesGames(id) && gamesError.value) void loadGames();
  if (id === "weekly-digest") void loadDigest();
}
function pluginWidget(id: string) {
  return pluginWidgets.value.find(
    (item) => `plugin:${item.pluginId}:${item.extensionId}` === id,
  );
}
async function saveWidgetConfiguration(values: UiValues) {
  const contribution = configuring.value;
  if (!contribution) return;
  const accountId = currentUser.value?.id;
  const id = `plugin:${contribution.pluginId}:${contribution.extensionId}`;
  configuringBusy.value = true;
  configurationError.value = null;
  try {
    const result = await queuePreferences({
      home_widget_config: {
        ...preferences.value.home_widget_config,
        [id]: values,
      },
    });
    if (currentUser.value?.id !== accountId) return;
    preferences.value = result.latest
      ? result.prefs
      : {
          ...preferences.value,
          home_widget_config: result.prefs.home_widget_config,
        };
    configuring.value = null;
  } catch (reason) {
    if (currentUser.value?.id === accountId)
      configurationError.value =
        reason instanceof Error
          ? reason.message
          : "Could not save widget options.";
  } finally {
    configuringBusy.value = false;
  }
}
async function saveHome(ids: string[]) {
  const accountId = currentUser.value?.id;
  saving.value = true;
  saveError.value = null;
  saved.value = false;
  try {
    const result = await queuePreferences({ home_widgets: [...ids] });
    if (currentUser.value?.id !== accountId) return;
    preferences.value = result.latest
      ? result.prefs
      : { ...preferences.value, home_widgets: result.prefs.home_widgets };
    showPicker.value = false;
    saved.value = true;
  } catch (reason) {
    if (currentUser.value?.id === accountId)
      saveError.value =
        reason instanceof Error ? reason.message : "Could not save Home.";
  } finally {
    saving.value = false;
  }
}
function openEdit(game: Game) {
  editingGame.value = game;
  showForm.value = true;
}
async function gameSaved() {
  showForm.value = false;
  editingGame.value = null;
  await loadGames();
}
function requestDelete(id: string) {
  showForm.value = false;
  editingGame.value = null;
  deletingGame.value = games.value.find((game) => game.id === id) ?? null;
  deleteError.value = null;
}
async function confirmDelete() {
  if (!deletingGame.value) return;
  deleting.value = true;
  deleteError.value = null;
  try {
    await deleteGame(deletingGame.value.id);
    deletingGame.value = null;
    await loadGames();
  } catch (reason) {
    deleteError.value =
      reason instanceof Error ? reason.message : "Could not delete the game.";
  } finally {
    deleting.value = false;
  }
}
</script>

<template>
  <PluginExtensionSlot
    v-if="hasHomeOverride && !replacementFailed"
    slot-id="home.replace"
    :context="{ host_page: 'home' }"
    @failed="replacementFailed = true"
  />
  <main v-else class="home-page">
    <AccountChip fixed />
    <div class="home-content">
      <p v-if="replacementFailed" role="status" class="ui-alert">
        The plugin Home page failed. Your Home is available below.
      </p>
      <PageHeader
        title="Home"
        :eyebrow="`Welcome back, ${currentUser?.username ?? ''}`"
        description="Your library, at your own pace."
      >
        <template #actions>
          <button
            type="button"
            class="ui-btn ui-btn-ghost"
            :disabled="!preferencesLoaded || Boolean(preferencesError)"
            @click="
              saveError = null;
              showPicker = true;
            "
          >
            Customize Home
          </button>
          <button
            type="button"
            class="ui-btn ui-btn-ghost"
            @click="showTour = true"
          >
            Quick tour
          </button>
        </template>
      </PageHeader>
      <nav class="home-shortcuts" aria-label="Library shortcuts">
        <router-link to="/games"
          >Games <span aria-hidden="true">↗</span></router-link
        >
        <router-link to="/movies"
          >Movies <span aria-hidden="true">↗</span></router-link
        >
        <router-link to="/collections"
          >Collections <span aria-hidden="true">↗</span></router-link
        >
      </nav>
      <p v-if="!preferencesLoaded" role="status">Loading your Home…</p>
      <div v-else-if="preferencesError" role="alert" class="ui-alert">
        {{ preferencesError }}
        <button
          type="button"
          class="ui-btn ui-btn-ghost"
          @click="loadSharedPreferences"
        >
          Retry
        </button>
      </div>
      <template v-else>
        <p v-if="saved" role="status" class="save-feedback">
          Home saved to your account.
        </p>
        <section
          v-if="!selected.length"
          class="home-empty"
          aria-labelledby="home-empty-title"
        >
          <p class="home-empty-eyebrow">A little room for you</p>
          <h2 id="home-empty-title">Make yourself at home.</h2>
          <p>
            Keep things quiet, or add your games in progress, favorite
            collections and personal goals.
          </p>
          <button
            type="button"
            class="ui-btn ui-btn-primary"
            @click="
              saveError = null;
              showPicker = true;
            "
          >
            Add widgets
          </button>
        </section>
        <div v-else class="home-widgets">
          <section
            v-for="widget in selected"
            :key="widget.id"
            class="home-widget"
            :class="{
              'wide-widget':
                ['continue-playing', 'recently-added'].includes(widget.id) ||
                widget.id.startsWith('collection:'),
            }"
            :aria-label="widget.title"
            :data-widget-id="widget.id"
          >
            <h2>{{ widget.title }}</h2>
            <p v-if="widget.available === false" class="widget-unavailable">
              {{ widget.description }}
            </p>
            <template v-else-if="widget.id.startsWith('plugin:')">
              <button
                v-if="pluginWidget(widget.id)?.widget?.configuration.length"
                type="button"
                class="ui-btn ui-btn-ghost widget-configure"
                :aria-label="`Customize ${widget.title}`"
                @click="
                  configuring = pluginWidget(widget.id)!;
                  configurationError = null;
                "
              >
                Options
              </button>
              <PluginHomeWidget
                v-if="pluginWidget(widget.id)"
                :contribution="pluginWidget(widget.id)!"
                :saved="preferences.home_widget_config[widget.id] ?? {}"
              />
            </template>
            <div
              v-else-if="widgetError(widget.id)"
              role="alert"
              class="ui-alert"
            >
              {{ widgetError(widget.id) }}
              <button
                type="button"
                class="ui-btn ui-btn-ghost"
                @click="retryWidget(widget.id)"
              >
                Retry
              </button>
            </div>
            <p
              v-else-if="widgetLoading(widget.id)"
              role="status"
              class="widget-loading"
            >
              Loading {{ widget.title.toLowerCase() }}…
            </p>
            <HomeCoreWidget
              v-else
              :widget-id="widget.id"
              :games="games"
              :digest="digest"
              @edit="openEdit"
              @collection="collectionGame = $event"
              @random="showRandom = true"
              @changed="loadGames"
            />
          </section>
        </div>
      </template>
    </div>
    <HomeWidgetPicker
      v-if="showPicker"
      :choices="choices"
      :selected="preferences.home_widgets"
      :busy="saving"
      :error="saveError || gamesError"
      :loading="gamesLoading"
      @close="showPicker = false"
      @save="saveHome"
    />
    <PluginWidgetConfiguration
      v-if="configuring?.widget"
      :key="`${configuring.pluginId}:${configuring.extensionId}`"
      :widget="configuring.widget"
      :saved="
        preferences.home_widget_config[
          `plugin:${configuring.pluginId}:${configuring.extensionId}`
        ] ?? {}
      "
      :busy="configuringBusy"
      :error="configurationError"
      @close="configuring = null"
      @save="saveWidgetConfiguration"
    />
    <UiModal
      v-if="showTour"
      title="A quick tour of your library"
      @close="showTour = false"
    >
      <ul class="tour-list">
        <li>
          <strong>Find anything fast</strong>
          <p>
            Press Ctrl/Cmd+K, or use Search in the menu, to find games,
            collections, goals and Settings.
          </p>
        </li>
        <li>
          <strong>Filter and save combinations</strong>
          <p>
            Use game filters and save a preset to return to the same view later.
          </p>
        </li>
        <li>
          <strong>Collections and goals</strong>
          <p>
            Group your games into collections and create personal bounties for
            what you want to finish.
          </p>
        </li>
        <li>
          <strong>Make Home yours</strong>
          <p>
            Add widgets and change their order with the up and down buttons.
            Your choices follow your account.
          </p>
        </li>
        <li>
          <strong>Keyboard shortcuts</strong>
          <p>
            Press ? or open Preferences → Keyboard shortcuts for the complete
            list.
          </p>
        </li>
      </ul>
      <template #footer
        ><button
          type="button"
          class="ui-btn ui-btn-primary"
          @click="showTour = false"
        >
          Got it
        </button></template
      >
    </UiModal>
    <GameFormModal
      v-if="showForm"
      :game="editingGame"
      @close="showForm = false"
      @saved="gameSaved"
      @delete="requestDelete"
    />
    <CollectionPickerModal
      v-if="collectionGame"
      :game="collectionGame"
      @close="collectionGame = null"
      @added="loadGames"
    />
    <RandomGamePicker
      v-if="showRandom"
      :games="games"
      @close="showRandom = false"
    />
    <UiModal
      v-if="deletingGame"
      :title="`Delete ${deletingGame.title}?`"
      description="This cannot be undone."
      :dismissible="!deleting"
      @close="deletingGame = null"
    >
      <p v-if="deleteError" role="alert" class="ui-alert">{{ deleteError }}</p>
      <template #footer>
        <button
          type="button"
          class="ui-btn ui-btn-ghost"
          :disabled="deleting"
          @click="deletingGame = null"
        >
          Cancel
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-danger"
          :disabled="deleting"
          @click="confirmDelete"
        >
          {{ deleting ? "Deleting…" : "Delete" }}
        </button>
      </template>
    </UiModal>
  </main>
</template>

<style scoped>
.home-page {
  box-sizing: border-box;
  padding: 80px var(--ui-edge-right) 32px var(--ui-edge-left);
  min-height: 100vh;
  color: var(--ui-text);
  font-family: var(--ui-font-family);
}
.home-content {
  max-width: var(--ui-content-width);
  margin: 0 auto;
}
.home-shortcuts {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 0 0 32px;
}
.home-shortcuts a {
  display: flex;
  align-items: center;
  gap: 20px;
  min-height: var(--ui-control-height);
  padding: 10px 16px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  text-decoration: none;
  background: var(--ui-surface);
  font-size: var(--ui-font-small);
}
.home-shortcuts a:hover {
  border-color: var(--ui-accent-line);
  color: var(--ui-accent-text);
}
.home-shortcuts span {
  color: var(--ui-faint);
}
.home-empty {
  max-width: 760px;
  padding: clamp(24px, 5vw, 64px);
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface);
}
.home-empty-eyebrow {
  color: var(--ui-accent-text);
  font-size: var(--ui-font-small);
  margin: 0 0 16px;
}
.home-empty h2 {
  font-size: clamp(1.5rem, 2.5vw, 2rem);
  font-weight: var(--ui-weight-title);
  letter-spacing: -0.025em;
  margin: 0 0 16px;
}
.home-empty > p:not(.home-empty-eyebrow) {
  max-width: 48ch;
  line-height: 1.65;
  color: var(--ui-dim);
  margin: 0 0 24px;
}
.home-widgets {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}
.home-widget {
  min-width: 0;
  padding: 24px;
  border-radius: var(--ui-radius-card);
  border: 1px solid var(--ui-border-soft);
  background: var(--ui-surface);
}
.home-widget h2 {
  margin: 0 0 20px;
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
  overflow-wrap: anywhere;
}
.wide-widget {
  grid-column: 1 / -1;
}
.widget-unavailable,
.widget-loading {
  color: var(--ui-dim);
  line-height: 1.6;
}
.save-feedback {
  margin-bottom: 18px;
  color: var(--ui-good);
  font-size: var(--ui-font-small);
}
.tour-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.tour-list li + li {
  margin-top: 20px;
}
.tour-list strong {
  font-weight: var(--ui-weight-heading);
}
.tour-list p {
  color: var(--ui-dim);
  margin: 6px 0 0;
}
@media (max-width: 760px) {
  .home-widgets {
    grid-template-columns: minmax(0, 1fr);
    gap: 18px;
  }
  .home-widget {
    padding: 20px;
  }
  .home-shortcuts {
    gap: 8px;
    margin-bottom: 24px;
  }
  .home-shortcuts a {
    padding: 10px 13px;
    gap: 12px;
  }
}
</style>
