<script setup lang="ts">
// The full game form: adding a game by hand and editing one. It follows the quick
// add dialog (header with the cover, the same fields, buttons and colours) and holds
// every field a game has. "Look up metadata" sits in the footer on every tab: it
// searches the providers, lists what would change field by field, and fills in only
// what is ticked.
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import GameArtPicker from "./GameArtPicker.vue";
import GameLookupPanel from "./GameLookupPanel.vue";
import PageSettingsEditor from "./PageSettingsEditor.vue";
import {
  attachGameAssetFromUrl,
  createGame,
  fetchGames,
  setPlaytimeSeconds,
  updateGame,
  uploadGameAsset,
} from "../services/games";
import type {
  Game,
  GameStatus,
  AchievementsProvider,
  GameRelationshipType,
} from "../types/game";
import type { GameLink, GameOwnership } from "../types/game";
import { preferences } from "../state/preferences";
import { resolvePage } from "../utils/gamePage";
import type { PageOverrides, PageSettings } from "../utils/gamePage";
import { fetchProviderCredentials } from "../services/settings";
import { localDateInputToUnixSeconds, toLocalDateInput } from "../utils/dates";
import { PRIORITY_OPTIONS, isFinished } from "../utils/priority";
import { RETRO_PLATFORM_OPTIONS } from "../utils/platforms";

const props = defineProps<{
  game?: Game | null;
}>();

const emit = defineEmits<{
  close: [];
  saved: [gameId: string];
  delete: [gameId: string];
}>();

const isEditing = computed(() => !!props.game);

// for the "parent game" picker, fetched here rather than threaded as a
// prop through every place this modal is opened from
const availableParentGames = ref<Game[]>([]);
// the ISO 4217 codes the API accepts, so a typo can't fail the save
const currencyCodes = ref<string[]>([]);
const hasSteamgriddbKey = ref(true);
onMounted(async () => {
  try {
    availableParentGames.value = (await fetchGames()).filter(
      (g) => g.id !== props.game?.id,
    );
  } catch {
    // the parent picker just stays empty
  }
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") return;
  fetchProviderCredentials()
    .then((status) => {
      hasSteamgriddbKey.value =
        !!status.SteamGridDB?.server_configured ||
        status.SteamGridDB?.status === "configured" ||
        status.SteamGridDB?.status === "connected";
    })
    .catch(() => {
      // the hint stays hidden
    });
  try {
    const response = await fetch("/api/currency-codes", {
      credentials: "include",
    });
    if (response.ok) {
      const body: { codes?: string[] } = await response.json();
      currencyCodes.value = body.codes ?? [];
    }
  } catch {
    // falls back to the free-text currency field
  }
});

// suggestions only: any other system can still be typed in
const PLATFORM_SUGGESTIONS = [
  "PC",
  "PlayStation 5",
  "PlayStation 4",
  "PlayStation 3",
  "PS Vita",
  "Xbox Series X|S",
  "Xbox One",
  "Xbox 360",
  "Nintendo Switch",
  "Nintendo Switch 2",
  "Wii U",
  "Wii",
  "Nintendo 3DS",
  "Nintendo DS",
  "Steam Deck",
  "Mac",
  "Linux",
  "Android",
  "iOS",
  ...RETRO_PLATFORM_OPTIONS,
];

const statuses: GameStatus[] = [
  "playing",
  "beaten",
  "mastered",
  "played",
  "on hold",
  "dropped",
  "backlog",
  "wishlist",
];

const RELATIONSHIP_TYPE_OPTIONS: {
  value: GameRelationshipType;
  label: string;
}[] = [
  { value: "mod", label: "Mod" },
  { value: "modpack", label: "Modpack" },
  { value: "expansion", label: "Expansion" },
  { value: "dlc", label: "DLC" },
  { value: "standalone_expansion", label: "Standalone expansion" },
  { value: "total_conversion", label: "Total conversion" },
];

const TABS = [
  "Basics",
  "Details",
  "Play",
  "Ratings and tags",
  "Artwork",
  "Links",
  "Ownership",
  "Advanced",
] as const;
type Tab = (typeof TABS)[number];
const activeTab = ref<Tab>("Basics");
// the artwork tab is built the first time it is opened, and kept after that, so
// choosing a picture and moving to another tab does not lose it
const artEverOpened = ref(false);
watch(activeTab, (tab) => {
  if (tab === "Artwork") artEverOpened.value = true;
});

// keep the current tab in view when the tab row scrolls (phones). Only the row is
// scrolled: scrollIntoView would also move the dialog, which hides its own tab bar.
const tabsEl = ref<HTMLElement | null>(null);
watch(activeTab, () =>
  nextTick(() => {
    const row = tabsEl.value;
    const tab = row?.querySelector<HTMLElement>(".gf-tab.active");
    if (!row || !tab) return;
    if (tab.offsetLeft < row.scrollLeft) row.scrollLeft = tab.offsetLeft - 8;
    else if (
      tab.offsetLeft + tab.offsetWidth >
      row.scrollLeft + row.clientWidth
    )
      row.scrollLeft = tab.offsetLeft + tab.offsetWidth - row.clientWidth + 8;
  }),
);

// ---- the fields ----
const title = ref(props.game?.title ?? "");
// the saved custom sorting name, blank when the library sorts by the title
const sortTitle = ref(props.game?.sortTitle ?? "");
const platform = ref(props.game?.platform ?? "");
const priority = ref(props.game?.priority ?? "");
const folderLocation = ref(props.game?.folderLocation ?? "");
const status = ref<GameStatus>(props.game?.status ?? "backlog");
const favorite = ref(props.game?.favorite ?? false);
const developer = ref(props.game?.developer ?? "");
const publisher = ref(props.game?.publisher ?? "");
const series = ref(props.game?.series ?? "");
const parentGameId = ref(props.game?.parentGameId ?? "");
const relationshipType = ref<GameRelationshipType | "">(
  props.game?.relationshipType ?? "",
);
const source = ref(props.game?.source ?? "");
const ageRating = ref(props.game?.ageRating ?? "");
const region = ref(props.game?.region ?? "");
const language = ref(props.game?.language ?? "");
const achievementsProvider = ref<AchievementsProvider>(
  props.game?.achievementsProvider ?? null,
);
const releaseDate = ref(props.game?.releaseDate ?? "");
// the local calendar day (what <input type="date"> shows); the stored value is a
// full timestamp, only sent back if it was changed, so saving the form doesn't
// reset the time a game was added to midnight
const initialDateAdded = toLocalDateInput(props.game?.dateAdded ?? new Date());
const dateAdded = ref(initialDateAdded);
const description = ref(props.game?.description ?? "");
const profilesEnabled = ref(props.game?.profilesEnabled ?? false);
const osrsStatsEnabled = ref(props.game?.osrsStatsEnabled ?? false);
watch(profilesEnabled, (enabled) => {
  if (!enabled) osrsStatsEnabled.value = false;
});
// this game's overrides of what its page shows (see Settings, Game page)
const pageOverrides = ref<PageOverrides>(
  JSON.parse(JSON.stringify(props.game?.pageSettings ?? {})),
);
const pageDefaults = computed<PageSettings>(() =>
  resolvePage(preferences.value.game_page, null),
);

// v-model on a type="number" input hands back a number once it's typed in, a
// string otherwise, so these must never assume either
const asText = (v: number | null | undefined) => (v != null ? String(v) : "");
const timeToBeatHours = ref<string | number>(
  asText(props.game?.timeToBeatHours),
);
const timeToBeatExtras = ref<string | number>(
  asText(props.game?.timeToBeatExtrasHours),
);
const timeToBeatCompletionist = ref<string | number>(
  asText(props.game?.timeToBeatCompletionistHours),
);
const timeToBeatAll = ref<string | number>(
  asText(props.game?.timeToBeatAllHours),
);

const initialPlaytimeHours = props.game
  ? Math.round(
      (props.game.platforms.reduce((sum, p) => sum + p.playtimeMinutes, 0) /
        60) *
        10,
    ) / 10
  : 0;
const playtimeHours = ref<string | number>(
  initialPlaytimeHours ? String(initialPlaytimeHours) : "",
);
const resumeNote = ref(props.game?.resumeNote ?? "");
const completionDate = ref(props.game?.completionDate ?? "");

const ratingOverall = ref<number | null>(props.game?.ratingOverall ?? null);
const ratingStory = ref<number | null>(props.game?.ratingStory ?? null);
const ratingGameplay = ref<number | null>(props.game?.ratingGameplay ?? null);
const ratingSound = ref<number | null>(props.game?.ratingSound ?? null);
const tagsInput = ref(props.game?.tags.join(", ") ?? "");
const featuresInput = ref(props.game?.features.join(", ") ?? "");
const collectionsInput = ref(props.game?.collections.join(", ") ?? "");

const links = ref<GameLink[]>(props.game?.links ? [...props.game.links] : []);
function addLink() {
  links.value.push({ label: "", url: "" });
}
function removeLink(index: number) {
  links.value.splice(index, 1);
}

const ownershipFormat = ref<GameOwnership["format"]>(
  props.game?.ownership.format ?? null,
);
const purchaseDate = ref(props.game?.ownership.purchaseDate ?? "");
const price = ref<number | null>(props.game?.ownership.price ?? null);
const priceCurrency = ref(props.game?.ownership.priceCurrency ?? "USD");
const condition = ref(props.game?.ownership.condition ?? "");

const saving = ref(false);
const error = ref<string | null>(null);

// ---- artwork: a file chosen here wins over a link, which wins over what is saved ----
const coverFile = ref<File | null>(null);
const bannerFile = ref<File | null>(null);
const pickedKeyArtUrl = ref<string | null>(null);
const pickedBannerUrl = ref<string | null>(null);
const coverLink = ref("");
const bannerLink = ref("");
const coverFileUrl = ref<string | null>(null);
const bannerFileUrl = ref<string | null>(null);

function revoke(url: string | null) {
  if (url) URL.revokeObjectURL(url);
}
function onCoverFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0] ?? null;
  revoke(coverFileUrl.value);
  coverFile.value = file;
  coverFileUrl.value = file ? URL.createObjectURL(file) : null;
  if (file) coverLink.value = "";
}
function onBannerFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0] ?? null;
  revoke(bannerFileUrl.value);
  bannerFile.value = file;
  bannerFileUrl.value = file ? URL.createObjectURL(file) : null;
  if (file) bannerLink.value = "";
}
function resetFileInputOnClick(e: Event) {
  // cleared before the picker opens so choosing the same file again still fires change
  (e.currentTarget as HTMLInputElement).value = "";
}
function useCoverLink() {
  const url = coverLink.value.trim();
  if (!url) return;
  revoke(coverFileUrl.value);
  coverFile.value = null;
  coverFileUrl.value = null;
  pickedKeyArtUrl.value = url;
}
function useBannerLink() {
  const url = bannerLink.value.trim();
  if (!url) return;
  revoke(bannerFileUrl.value);
  bannerFile.value = null;
  bannerFileUrl.value = null;
  pickedBannerUrl.value = url;
}
// picking from the provider options replaces any file or link
watch(pickedKeyArtUrl, (url) => {
  if (url && url !== coverLink.value.trim()) {
    revoke(coverFileUrl.value);
    coverFile.value = null;
    coverFileUrl.value = null;
  }
});
watch(pickedBannerUrl, (url) => {
  if (url && url !== bannerLink.value.trim()) {
    revoke(bannerFileUrl.value);
    bannerFile.value = null;
    bannerFileUrl.value = null;
  }
});
onBeforeUnmount(() => {
  revoke(coverFileUrl.value);
  revoke(bannerFileUrl.value);
});

const coverPreview = computed(
  () =>
    coverFileUrl.value ??
    pickedKeyArtUrl.value ??
    props.game?.coverImageUrl ??
    null,
);
const bannerPreview = computed(
  () =>
    bannerFileUrl.value ??
    pickedBannerUrl.value ??
    props.game?.bannerImageUrl ??
    null,
);
const subtitle = computed(() =>
  [
    developer.value.trim(),
    releaseDate.value ? releaseDate.value.slice(0, 4) : "",
    platform.value.trim(),
  ]
    .filter(Boolean)
    .join(" · "),
);

// when editing, the folder name is already real data, don't let the
// title-blur auto-suggest silently overwrite it
const folderTouched = ref(isEditing.value);
function folderFromTitle(value: string): string {
  return value
    .trim()
    .replace(/[^A-Za-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
function suggestFolderFromTitle() {
  if (folderTouched.value) return;
  folderLocation.value = folderFromTitle(title.value);
}

// ---- look up metadata ----
// The panel lists what a provider has and hands back the fields that were ticked.
const lookupOpen = ref(false);
const lookupNote = ref<string | null>(null);
const lookupCurrent = computed<Record<string, string>>(() => ({
  title: title.value,
  description: description.value,
  developer: developer.value,
  publisher: publisher.value,
  series: series.value,
  releaseDate: releaseDate.value,
  ageRating: ageRating.value,
  timeToBeatHours: String(timeToBeatHours.value),
  timeToBeatExtras: String(timeToBeatExtras.value),
  timeToBeatCompletionist: String(timeToBeatCompletionist.value),
  timeToBeatAll: String(timeToBeatAll.value),
  tags: tagsInput.value,
  features: featuresInput.value,
  source: source.value,
  links: JSON.stringify(links.value),
  linksCount: String(links.value.length),
}));

function applyLookup(
  changes: { key: string; value: unknown }[],
  provider: string,
) {
  const text = (v: unknown) => String(v ?? "");
  for (const { key, value } of changes) {
    switch (key) {
      case "title":
        title.value = text(value);
        suggestFolderFromTitle();
        break;
      case "description":
        description.value = text(value);
        break;
      case "developer":
        developer.value = text(value);
        break;
      case "publisher":
        publisher.value = text(value);
        break;
      case "series":
        series.value = text(value);
        break;
      case "releaseDate":
        releaseDate.value = text(value);
        break;
      case "ageRating":
        ageRating.value = text(value);
        break;
      case "timeToBeatHours":
        timeToBeatHours.value = text(value);
        break;
      case "timeToBeatExtras":
        timeToBeatExtras.value = text(value);
        break;
      case "timeToBeatCompletionist":
        timeToBeatCompletionist.value = text(value);
        break;
      case "timeToBeatAll":
        timeToBeatAll.value = text(value);
        break;
      case "tags":
        tagsInput.value = text(value);
        break;
      case "features":
        featuresInput.value = text(value);
        break;
      case "source":
        source.value = text(value);
        break;
      case "links":
        links.value = value as GameLink[];
        break;
      case "cover":
        pickedKeyArtUrl.value = text(value);
        coverLink.value = "";
        break;
      case "banner":
        pickedBannerUrl.value = text(value);
        bannerLink.value = "";
        break;
    }
  }
  lookupOpen.value = false;
  lookupNote.value = changes.length
    ? `Filled ${changes.length} field${changes.length === 1 ? "" : "s"} from ${provider}. Review them, then save.`
    : null;
}

// ---- saving ----
function validate(): boolean {
  if (!title.value.trim()) {
    error.value = "Title is required.";
    activeTab.value = "Basics";
    return false;
  }
  if (!isEditing.value && !folderLocation.value.trim()) {
    error.value = "Folder name is required.";
    activeTab.value = "Basics";
    return false;
  }
  return true;
}

const splitList = (text: string) =>
  text
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

async function submit() {
  if (!validate()) return;

  saving.value = true;
  error.value = null;

  // a cleared number box reads "" rather than null, which the server rejects
  const num = (v: number | null | ""): number | null =>
    v === "" || v === null || Number.isNaN(v) ? null : v;
  const hoursOrNull = (v: string | number) =>
    String(v).trim() ? Number(v) : null;
  const input = {
    title: title.value.trim(),
    sortTitle: sortTitle.value.trim() || null,
    folderLocation: folderLocation.value.trim(),
    status: status.value,
    description: description.value.trim() || null,
    developer: developer.value.trim() || null,
    publisher: publisher.value.trim() || null,
    series: series.value.trim() || null,
    parentGameId: parentGameId.value || null,
    relationshipType: parentGameId.value
      ? relationshipType.value || null
      : null,
    releaseDate: releaseDate.value || null,
    dateAdded: dateAdded.value || null,
    createdAt:
      dateAdded.value && dateAdded.value !== initialDateAdded
        ? localDateInputToUnixSeconds(dateAdded.value)
        : null,
    completionDate: completionDate.value || null,
    source: source.value.trim() || null,
    platform: platform.value.trim() || null,
    priority: priority.value || null,
    ageRating: ageRating.value.trim() || null,
    timeToBeatHours: hoursOrNull(timeToBeatHours.value),
    timeToBeatExtrasHours: hoursOrNull(timeToBeatExtras.value),
    timeToBeatCompletionistHours: hoursOrNull(timeToBeatCompletionist.value),
    timeToBeatAllHours: hoursOrNull(timeToBeatAll.value),
    resumeNote: resumeNote.value.trim() || null,
    region: region.value.trim() || null,
    language: language.value.trim() || null,
    achievementsProvider: achievementsProvider.value,
    ratingOverall: num(ratingOverall.value),
    ratingStory: num(ratingStory.value),
    ratingGameplay: num(ratingGameplay.value),
    ratingSound: num(ratingSound.value),
    tags: splitList(tagsInput.value),
    features: splitList(featuresInput.value),
    links: links.value.filter((l) => l.label.trim() && l.url.trim()),
    ownership: {
      format: ownershipFormat.value,
      purchaseDate: purchaseDate.value || null,
      price: num(price.value),
      priceCurrency:
        num(price.value) !== null
          ? priceCurrency.value.trim().toUpperCase() || "USD"
          : null,
      condition: condition.value.trim() || null,
    },
    favorite: favorite.value,
    collections: splitList(collectionsInput.value),
    profilesEnabled: profilesEnabled.value,
    pageSettings: pageOverrides.value,
    osrsStatsEnabled: osrsStatsEnabled.value,
  };

  try {
    const savedGame = isEditing.value
      ? await updateGame(props.game!.id, input)
      : await createGame(input);

    if (import.meta.env.VITE_USE_MOCK_DATA !== "true") {
      const hours = String(playtimeHours.value).trim()
        ? Number(playtimeHours.value)
        : 0;
      if (
        Number.isFinite(hours) &&
        Math.abs(hours - initialPlaytimeHours) > 0.01
      ) {
        await setPlaytimeSeconds(savedGame.id, Math.round(hours * 3600));
      }
      // an explicitly chosen file always wins over a link or a provider's picture
      if (coverFile.value) {
        await uploadGameAsset(savedGame.id, "key_art", coverFile.value);
      } else if (pickedKeyArtUrl.value) {
        await attachGameAssetFromUrl(
          savedGame.id,
          "key_art",
          pickedKeyArtUrl.value,
        );
      }
      if (bannerFile.value) {
        await uploadGameAsset(savedGame.id, "banner", bannerFile.value);
      } else if (pickedBannerUrl.value) {
        await attachGameAssetFromUrl(
          savedGame.id,
          "banner",
          pickedBannerUrl.value,
        );
      }
    }

    emit("saved", savedGame.id);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Could not save game";
  } finally {
    saving.value = false;
  }
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape" && !lookupOpen.value) emit("close");
}
onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <div class="gf-overlay" @click.self="emit('close')">
    <div class="gf-card" role="dialog" aria-modal="true">
      <header class="gf-header">
        <button
          type="button"
          class="gf-cover"
          :class="{ empty: !coverPreview }"
          :style="
            coverPreview ? { backgroundImage: `url(${coverPreview})` } : {}
          "
          aria-label="Open artwork"
          title="Artwork"
          @click="activeTab = 'Artwork'"
        ></button>
        <div class="gf-titles">
          <div class="gf-kicker">
            {{ isEditing ? "Edit game" : "Add game" }}
          </div>
          <h3>{{ title.trim() || "Untitled game" }}</h3>
          <p v-if="subtitle" class="sub">{{ subtitle }}</p>
        </div>
        <button
          type="button"
          class="gf-close"
          aria-label="Close"
          @click="emit('close')"
        >
          &#10005;
        </button>
      </header>

      <nav ref="tabsEl" class="gf-tabs" aria-label="Game details">
        <button
          v-for="tab in TABS"
          :key="tab"
          type="button"
          class="gf-tab"
          :class="{ active: activeTab === tab }"
          @click="activeTab = tab"
        >
          {{ tab }}
        </button>
      </nav>

      <form id="game-form" class="gf-body" @submit.prevent="submit">
        <p v-if="lookupNote" class="gf-note">{{ lookupNote }}</p>

        <div v-if="activeTab === 'Basics'" class="gf-panel">
          <p class="gf-section">Identity</p>
          <div class="gf-grid">
            <label class="gf-field full">
              <span>Title</span>
              <input
                v-model="title"
                type="text"
                required
                @blur="suggestFolderFromTitle"
              />
            </label>
            <label class="gf-field">
              <span>Sorting name</span>
              <input
                v-model="sortTitle"
                type="text"
                placeholder="Defaults to the title"
              />
            </label>
            <label class="gf-field">
              <span>Folder name</span>
              <input
                v-model="folderLocation"
                type="text"
                :required="!isEditing"
                pattern="[A-Za-z0-9_\-]+"
                title="Letters, numbers, underscores and hyphens only"
                :placeholder="
                  isEditing ? 'Leave blank to keep the current one' : ''
                "
                @input="folderTouched = true"
              />
            </label>
          </div>

          <p class="gf-section">Library</p>
          <div class="gf-grid">
            <label class="gf-field">
              <span>Status</span>
              <select v-model="status">
                <option v-for="s in statuses" :key="s" :value="s">
                  {{ s }}
                </option>
              </select>
            </label>
            <label class="gf-field">
              <span>Priority</span>
              <select v-model="priority">
                <option value="">None</option>
                <option
                  v-for="option in PRIORITY_OPTIONS"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
              <small v-if="priority && isFinished(status)" class="gf-small">
                Finished games are left out of priority sorting and the random
                picker.
              </small>
            </label>
            <label class="gf-field">
              <span>Platform</span>
              <input
                v-model="platform"
                type="text"
                list="game-platform-suggestions"
                placeholder="PC, PlayStation 5, Switch"
              />
              <datalist id="game-platform-suggestions">
                <option
                  v-for="option in PLATFORM_SUGGESTIONS"
                  :key="option"
                  :value="option"
                />
              </datalist>
            </label>
            <label class="gf-field">
              <span>Source</span>
              <input
                v-model="source"
                type="text"
                placeholder="Steam, GOG, physical"
              />
            </label>
            <label class="gf-field">
              <span>Date added to library</span>
              <input v-model="dateAdded" type="date" />
            </label>
            <label class="gf-check">
              <input v-model="favorite" type="checkbox" />
              <span>Favorite</span>
            </label>
          </div>
        </div>

        <div v-else-if="activeTab === 'Details'" class="gf-panel">
          <p class="gf-section">About</p>
          <div class="gf-grid">
            <label class="gf-field full">
              <span>Description</span>
              <textarea v-model="description" rows="5"></textarea>
            </label>
            <label class="gf-field">
              <span>Developer</span>
              <input v-model="developer" type="text" />
            </label>
            <label class="gf-field">
              <span>Publisher</span>
              <input v-model="publisher" type="text" />
            </label>
            <label class="gf-field">
              <span>Series</span>
              <input v-model="series" type="text" />
            </label>
            <label class="gf-field">
              <span>Release date</span>
              <input v-model="releaseDate" type="date" />
            </label>
          </div>

          <p class="gf-section">Release details</p>
          <div class="gf-grid">
            <label class="gf-field">
              <span>Age rating</span>
              <input
                v-model="ageRating"
                type="text"
                placeholder="ESRB M, PEGI 18"
              />
            </label>
            <label class="gf-field">
              <span>Region</span>
              <input v-model="region" type="text" placeholder="NA, PAL, JP" />
            </label>
            <label class="gf-field">
              <span>Language</span>
              <input
                v-model="language"
                type="text"
                placeholder="English, Japanese"
              />
            </label>
          </div>
        </div>

        <div v-else-if="activeTab === 'Play'" class="gf-panel">
          <p class="gf-section">Progress</p>
          <div class="gf-grid">
            <label class="gf-field">
              <span>Playtime (hours)</span>
              <input
                v-model="playtimeHours"
                type="number"
                min="0"
                step="0.1"
                placeholder="0"
              />
            </label>
            <label class="gf-field">
              <span>100% completion date</span>
              <input v-model="completionDate" type="date" />
            </label>
            <label class="gf-field full">
              <span>Where you left off</span>
              <textarea
                v-model="resumeNote"
                rows="3"
                maxlength="2000"
                placeholder="What to do when you pick this game back up"
              ></textarea>
            </label>
          </div>

          <p class="gf-section">Time to beat (hours)</p>
          <div class="gf-grid four">
            <label class="gf-field">
              <span>Main story</span>
              <input
                v-model="timeToBeatHours"
                type="number"
                min="0"
                step="0.1"
              />
            </label>
            <label class="gf-field">
              <span>Main story and extras</span>
              <input
                v-model="timeToBeatExtras"
                type="number"
                min="0"
                step="0.1"
              />
            </label>
            <label class="gf-field">
              <span>Completionist</span>
              <input
                v-model="timeToBeatCompletionist"
                type="number"
                min="0"
                step="0.1"
              />
            </label>
            <label class="gf-field">
              <span>All play styles</span>
              <input v-model="timeToBeatAll" type="number" min="0" step="0.1" />
            </label>
          </div>
        </div>

        <div v-else-if="activeTab === 'Ratings and tags'" class="gf-panel">
          <p class="gf-section">Your ratings (0 to 10)</p>
          <div class="gf-grid four">
            <label class="gf-field">
              <span>Atmosphere</span>
              <input
                v-model.number="ratingOverall"
                type="number"
                min="0"
                max="10"
                step="0.1"
              />
            </label>
            <label class="gf-field">
              <span>Story</span>
              <input
                v-model.number="ratingStory"
                type="number"
                min="0"
                max="10"
                step="0.1"
              />
            </label>
            <label class="gf-field">
              <span>Gameplay</span>
              <input
                v-model.number="ratingGameplay"
                type="number"
                min="0"
                max="10"
                step="0.1"
              />
            </label>
            <label class="gf-field">
              <span>Sound</span>
              <input
                v-model.number="ratingSound"
                type="number"
                min="0"
                max="10"
                step="0.1"
              />
            </label>
          </div>

          <p class="gf-section">Organize</p>
          <div class="gf-grid">
            <label class="gf-field full">
              <span>Tags (comma separated)</span>
              <input
                v-model="tagsInput"
                type="text"
                placeholder="Action RPG, Souls-like"
              />
            </label>
            <label class="gf-field full">
              <span>Features (comma separated)</span>
              <input
                v-model="featuresInput"
                type="text"
                placeholder="Achievements, Cloud saves"
              />
            </label>
            <label class="gf-field full">
              <span>Collections (comma separated)</span>
              <input
                v-model="collectionsInput"
                type="text"
                placeholder="Steam, Backlog 2026"
              />
            </label>
          </div>
        </div>

        <div v-else-if="activeTab === 'Links'" class="gf-panel">
          <p class="gf-section">Links</p>
          <div v-for="(link, index) in links" :key="index" class="gf-link-edit">
            <label class="gf-field">
              <span>Label</span>
              <input
                v-model="link.label"
                type="text"
                placeholder="Steam store page"
              />
            </label>
            <label class="gf-field">
              <span>URL</span>
              <input v-model="link.url" type="url" placeholder="https://" />
            </label>
            <button
              type="button"
              class="gf-remove"
              aria-label="Remove link"
              @click="removeLink(index)"
            >
              &#10005;
            </button>
          </div>
          <p v-if="!links.length" class="gf-hint">No links.</p>
          <button type="button" class="gf-btn" @click="addLink">
            Add link
          </button>
        </div>

        <div v-else-if="activeTab === 'Ownership'" class="gf-panel">
          <p class="gf-section">Purchase</p>
          <div class="gf-grid">
            <label class="gf-field">
              <span>Format</span>
              <select v-model="ownershipFormat">
                <option :value="null">Unspecified</option>
                <option value="digital">Digital</option>
                <option value="physical">Physical</option>
              </select>
            </label>
            <label class="gf-field">
              <span>Purchase date</span>
              <input v-model="purchaseDate" type="date" />
            </label>
            <label class="gf-field">
              <span>Price</span>
              <input v-model.number="price" type="number" min="0" step="0.01" />
            </label>
            <label class="gf-field">
              <span>Currency</span>
              <select v-if="currencyCodes.length" v-model="priceCurrency">
                <option v-for="code in currencyCodes" :key="code" :value="code">
                  {{ code }}
                </option>
              </select>
              <input
                v-else
                v-model="priceCurrency"
                type="text"
                placeholder="USD"
                maxlength="3"
              />
            </label>
            <label v-if="ownershipFormat === 'physical'" class="gf-field full">
              <span>Condition</span>
              <input
                v-model="condition"
                type="text"
                placeholder="CIB, disc only, box wear"
              />
            </label>
          </div>
        </div>

        <div v-else-if="activeTab === 'Advanced'" class="gf-panel">
          <p class="gf-section">Related games</p>
          <div class="gf-grid">
            <label class="gf-field">
              <span>Parent game</span>
              <select v-model="parentGameId">
                <option value="">None, this is its own game</option>
                <option
                  v-for="g in availableParentGames"
                  :key="g.id"
                  :value="g.id"
                >
                  {{ g.title }}
                </option>
              </select>
            </label>
            <label class="gf-field">
              <span>Relationship</span>
              <select v-model="relationshipType" :disabled="!parentGameId">
                <option value="">N/A</option>
                <option
                  v-for="opt in RELATIONSHIP_TYPE_OPTIONS"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </option>
              </select>
              <small v-if="!parentGameId" class="gf-small">
                Choose a parent game first.
              </small>
            </label>
          </div>

          <p class="gf-section">Achievements and accounts</p>
          <div class="gf-grid">
            <label class="gf-field">
              <span>Achievements from</span>
              <select v-model="achievementsProvider">
                <option :value="null">Default</option>
                <option value="native">Native</option>
                <option value="retroachievements">RetroAchievements</option>
              </select>
            </label>
            <label class="gf-check full">
              <input v-model="profilesEnabled" type="checkbox" />
              <span>
                Track multiple accounts on this game
                <small
                  >Adds an account switcher with its own checklist and media for
                  each account.</small
                >
              </span>
            </label>
            <label v-if="profilesEnabled" class="gf-check full">
              <input v-model="osrsStatsEnabled" type="checkbox" />
              <span>
                Use OSRS stats (WiseOldMan)
                <small
                  >Adds skill and boss syncing from wiseoldman.net. Only for Old
                  School RuneScape.</small
                >
              </span>
            </label>
          </div>

          <p class="gf-section">Game page</p>
          <p class="gf-hint">
            What this game's page shows. Anything left on Default follows
            Settings, Game page.
          </p>
          <PageSettingsEditor
            :model-value="pageOverrides"
            :defaults="pageDefaults"
            @update:model-value="pageOverrides = $event as PageOverrides"
          />
        </div>

        <div
          v-if="artEverOpened"
          v-show="activeTab === 'Artwork'"
          class="gf-panel"
        >
          <div class="gf-art-grid">
            <div class="gf-art-slot">
              <p class="gf-section">Cover</p>
              <div class="gf-art-row">
                <div
                  class="gf-art-preview tall"
                  :style="
                    coverPreview
                      ? { backgroundImage: `url(${coverPreview})` }
                      : {}
                  "
                ></div>
                <div class="gf-art-actions">
                  <label class="gf-btn">
                    Upload a file
                    <input
                      type="file"
                      accept="image/*"
                      class="gf-hidden"
                      @click="resetFileInputOnClick"
                      @change="onCoverFile"
                    />
                  </label>
                  <div class="gf-link-row">
                    <input
                      v-model="coverLink"
                      type="url"
                      placeholder="Paste an image link"
                      @keydown.enter.prevent="useCoverLink"
                    />
                    <button type="button" class="gf-btn" @click="useCoverLink">
                      Use
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div class="gf-art-slot">
              <p class="gf-section">Banner</p>
              <div class="gf-art-row">
                <div
                  class="gf-art-preview wide"
                  :style="
                    bannerPreview
                      ? { backgroundImage: `url(${bannerPreview})` }
                      : {}
                  "
                ></div>
                <div class="gf-art-actions">
                  <label class="gf-btn">
                    Upload a file
                    <input
                      type="file"
                      accept="image/*"
                      class="gf-hidden"
                      @click="resetFileInputOnClick"
                      @change="onBannerFile"
                    />
                  </label>
                  <div class="gf-link-row">
                    <input
                      v-model="bannerLink"
                      type="url"
                      placeholder="Paste an image link"
                      @keydown.enter.prevent="useBannerLink"
                    />
                    <button type="button" class="gf-btn" @click="useBannerLink">
                      Use
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <GameArtPicker
              v-if="title.trim().length >= 2"
              v-model:cover="pickedKeyArtUrl"
              v-model:banner="pickedBannerUrl"
              :title="title.trim()"
              :provider="source.trim() || 'Steam'"
              provider-id=""
              :current-cover="null"
              class="gf-art-picker"
            />
            <p v-if="!hasSteamgriddbKey" class="gf-hint">
              Add a SteamGridDB key under Settings, Library, Metadata to pick
              from more covers and banners.
            </p>
            <p class="gf-hint">
              A picture you choose is saved and shown as soon as you save.
            </p>
          </div>
        </div>

        <div v-if="error" class="gf-error">{{ error }}</div>
      </form>

      <footer class="gf-footer">
        <button
          v-if="isEditing"
          type="button"
          class="gf-btn danger"
          @click="emit('delete', props.game!.id)"
        >
          Delete game
        </button>
        <button type="button" class="gf-btn" @click="lookupOpen = true">
          Look up metadata
        </button>
        <span class="gf-spacer"></span>
        <button type="button" class="gf-btn" @click="emit('close')">
          Cancel
        </button>
        <button
          type="submit"
          form="game-form"
          class="gf-btn solid"
          :disabled="saving"
        >
          {{ saving ? "Saving…" : isEditing ? "Save changes" : "Add game" }}
        </button>
      </footer>

      <GameLookupPanel
        v-if="lookupOpen"
        :adding="!isEditing"
        :initial-query="title"
        :current-cover="coverPreview"
        :current="lookupCurrent"
        @close="lookupOpen = false"
        @apply="applyLookup"
      />
    </div>
  </div>
</template>

<style scoped>
.gf-overlay {
  --bg: var(--ui-bg);
  --surface: var(--ui-surface);
  --surface-2: var(--ui-surface-2);
  --border: var(--ui-border);
  --border-soft: var(--ui-border-soft);
  --accent: var(--ui-accent);
  --accent-soft: var(--ui-accent-soft);
  --accent-line: var(--ui-accent-line);
  --danger: var(--ui-danger-muted);
  --text: var(--ui-text);
  --text-dim: var(--ui-dim);
  --text-faint: #666;
  position: fixed;
  inset: 0;
  z-index: var(--ui-z-modal, 100);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: color-mix(in srgb, var(--ui-scrim-base) 70%, transparent);
  color: var(--text);
}
.gf-overlay * {
  box-sizing: border-box;
}
.gf-card {
  position: relative;
  display: flex;
  flex-direction: column;
  width: min(880px, 100%);
  /* one height for every tab, so the dialog does not jump when the tab changes */
  height: min(720px, 92vh);
  overflow: hidden;
  background: var(--ui-popover, var(--ui-popover));
  border: 1px solid var(--border);
  border-radius: var(--ui-radius-dialog, 14px);
}

/* header: the cover and the titles, the way the quick add form starts */
.gf-header {
  flex: none;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: linear-gradient(160deg, var(--accent-soft), transparent 70%);
  border-bottom: 1px solid var(--border-soft);
}
.gf-cover {
  position: relative;
  flex: none;
  width: 64px;
  height: 90px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background-color: var(--surface);
  background-size: cover;
  background-position: center;
  cursor: pointer;
  overflow: hidden;
}
.gf-cover:hover {
  border-color: var(--accent-line);
}
.gf-titles {
  flex: 1;
  min-width: 0;
}
.gf-kicker {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
}
.gf-titles h3 {
  margin: 2px 0 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gf-titles .sub {
  margin: 2px 0 0;
  font-size: 0.8rem;
  color: var(--text-faint);
}
.gf-close {
  flex: none;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--text-dim);
  font-size: 1rem;
  cursor: pointer;
}
.gf-close:hover {
  background: var(--surface-2);
  color: var(--text);
}

/* the artwork tab */
.gf-art-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 20px;
}
.gf-art-grid .gf-art-picker,
.gf-art-grid > .gf-hint {
  grid-column: 1 / -1;
}
.gf-art-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.gf-art-preview {
  flex: none;
  border: 1px solid var(--border);
  border-radius: 8px;
  background-color: var(--surface-2);
  background-size: cover;
  background-position: center;
}
.gf-art-preview.tall {
  width: 76px;
  height: 108px;
}
.gf-art-preview.wide {
  width: 150px;
  height: 56px;
}
.gf-art-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  flex: 1;
}
.gf-link-row {
  display: flex;
  gap: 6px;
}
.gf-link-row input {
  min-width: 0;
}
.gf-art-grid .gf-hint {
  margin: 0;
}
.gf-art-slot .gf-section {
  margin-top: 0;
}
.gf-hidden {
  display: none;
}

/* tabs */
.gf-tabs {
  flex: none;
  display: flex;
  gap: 4px;
  align-self: flex-start;
  max-width: calc(100% - 40px);
  margin: 12px 20px 0;
  padding: 5px;
  /* the same bar as the tabs on the game and media pages */
  background: var(--surface);
  border-radius: 10px;
  overflow-x: auto;
  scrollbar-width: none;
}
.gf-tabs::-webkit-scrollbar {
  display: none;
}
.gf-tab {
  flex: none;
  padding: 8px 16px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--text-dim);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.gf-tab:hover {
  color: var(--text);
}
.gf-tab.active {
  background: var(--accent);
  color: var(--ui-on-accent);
}
.gf-tab:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

/* body and fields, the same look as the quick add form */
.gf-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 20px 20px;
}
.gf-section {
  margin: 18px 0 8px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-faint);
}
.gf-panel > .gf-section:first-child {
  margin-top: 0;
}
.gf-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.gf-grid.four {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.gf-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.gf-field.full,
.gf-check.full {
  grid-column: 1 / -1;
}
.gf-field > span {
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--text-dim);
}
.gf-field input,
.gf-field select,
.gf-field textarea,
.gf-link-row input,
.gf-lookup-search input {
  width: 100%;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 8px;
  padding: 9px 11px;
  font: inherit;
  font-size: 0.86rem;
}
.gf-field textarea {
  resize: vertical;
  min-height: 70px;
}
.gf-field input:focus,
.gf-field select:focus,
.gf-field textarea:focus,
.gf-link-row input:focus,
.gf-lookup-search input:focus {
  outline: none;
  border-color: var(--accent-line);
}
.gf-field select:disabled {
  opacity: 0.5;
}
.gf-small {
  font-size: 0.72rem;
  color: var(--text-faint);
}
.gf-check {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  align-self: end;
  font-size: 0.86rem;
  color: var(--text);
  padding: 8px 0;
}
.gf-check input {
  margin-top: 3px;
  accent-color: var(--accent);
}
.gf-check small {
  display: block;
  margin-top: 2px;
  font-size: 0.74rem;
  color: var(--text-faint);
}
.gf-hint {
  margin: 4px 0 10px;
  font-size: 0.78rem;
  color: var(--text-faint);
  line-height: 1.5;
}
.gf-note {
  margin: 0 0 14px;
  padding: 8px 12px;
  border: 1px solid var(--accent-line);
  border-radius: 8px;
  background: var(--accent-soft);
  font-size: 0.8rem;
  color: var(--text);
}
.gf-error {
  margin-top: 14px;
  padding: 8px 12px;
  border: 1px solid color-mix(in srgb, var(--ui-danger-muted) 40%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--ui-danger-muted) 12%, transparent);
  color: var(--danger);
  font-size: 0.82rem;
}
.gf-link-edit {
  display: grid;
  grid-template-columns: 1fr 2fr auto;
  gap: 10px;
  align-items: end;
  margin-bottom: 10px;
}
.gf-remove {
  width: 34px;
  height: 36px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-2);
  color: var(--text-dim);
  cursor: pointer;
}
.gf-remove:hover {
  color: var(--danger);
  border-color: color-mix(in srgb, var(--ui-danger-muted) 40%, transparent);
}

/* footer */
.gf-footer {
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--border-soft);
  background: var(--surface);
}
.gf-spacer {
  flex: 1;
}
.gf-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: transparent;
  color: var(--text-dim);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.gf-btn:hover {
  color: var(--text);
  border-color: var(--accent-line);
}
.gf-btn.solid {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--ui-on-accent);
}
.gf-btn.solid:hover {
  filter: brightness(1.08);
}
.gf-btn.solid:disabled {
  opacity: 0.6;
  cursor: default;
}
.gf-btn.danger {
  color: var(--danger);
}
.gf-btn.danger:hover {
  border-color: color-mix(in srgb, var(--ui-danger-muted) 50%, transparent);
}
.gf-btn:focus-visible,
.gf-tab:focus-visible,
.gf-result:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

@media (max-width: 720px) {
  .gf-grid,
  .gf-grid.four {
    grid-template-columns: 1fr;
  }
  .gf-link-edit {
    grid-template-columns: 1fr auto;
  }
  .gf-link-edit .gf-field:nth-child(2) {
    grid-column: 1 / -1;
    order: 3;
  }
  .gf-footer {
    flex-wrap: wrap;
  }
}
</style>
