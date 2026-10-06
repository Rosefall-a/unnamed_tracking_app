import { ref, reactive, onMounted } from "vue";

import { currentUser, checkAuth } from "../state/auth";
import { updateProfile } from "../services/auth";
import { fetchPsnStatus, connectPsn, disconnectPsn } from "../services/psn";
import type { PsnStatus } from "../services/psn";
import {
  fetchProviderCredentials,
  saveProviderCredentials,
  deleteProviderCredentials,
  fetchScanSettings,
  updateScanSettings,
  fetchAppIntegrations,
  updateAppIntegrations,
} from "../services/settings";
import type { ProviderCredentialStatus } from "../services/settings";
import { syncLibrary } from "../services/librarySync";
import type { LibrarySyncProvider } from "../services/librarySync";
import {
  startTask,
  completeTask,
  errorTask,
  addFeedItem,
} from "../state/taskProgress";
export function useMetadataSources() {
  // small colored monogram badge per provider, no real logos bundled, so a
  // distinct brand-ish color + short mark stands in, RomM-style icon tile
  interface CardVisual {
    bg: string;
    fg: string;
    mark: string;
  }
  // short one-liner shown on every tile so the grid stays scannable without
  // hovering, the fuller description still lives in the `title` tooltip
  const SHORT_DESC: Record<string, string> = {
    Steam: "Public store data, no key needed",
    SteamGridDB: "Cover art & hero banners",
    IGDB: "General metadata & art (app-wide key)",
    TMDB: "Movie metadata & posters (app-wide key)",
    OMDb: "IMDb-backed movie fallback source (app-wide key)",
    TVDB: "TV show franchise & relations data (app-wide key)",
    GiantBomb: "General metadata & art",
    ScreenScraper: "Retro box art & screenshots",
    GOG: "Metadata search, no key needed",
    LaunchBox: "Local app, not a cloud API",
    RetroAchievements: "Retro metadata & achievements",
    PlayStation: "Trophies & PSN Store data",
    Xbox: "Saved only: no live pull yet",
    HowLongToBeat: "Time-to-beat data",
  };

  const VISUALS: Record<string, CardVisual> = {
    Steam: { bg: "#12202e", fg: "#66c0f4", mark: "S" },
    SteamGridDB: { bg: "#0e3b3b", fg: "#2dd4bf", mark: "Gr" },
    IGDB: { bg: "#2b1c4a", fg: "#a78bfa", mark: "IG" },
    TMDB: { bg: "#01283d", fg: "#5dd9c1", mark: "TM" },
    OMDb: { bg: "#2a2205", fg: "#f5c518", mark: "OM" },
    TVDB: { bg: "#1a2a3d", fg: "#7ba7d9", mark: "TV" },
    GiantBomb: { bg: "#3d2f00", fg: "#fbbf24", mark: "GB" },
    RetroAchievements: { bg: "#3b0a0a", fg: "#f87171", mark: "RA" },
    ScreenScraper: { bg: "#1a3d0a", fg: "#86efac", mark: "SS" },
    Xbox: { bg: "#0a2e0a", fg: "#4ade80", mark: "Xb" },
    GOG: { bg: "#2a1a3d", fg: "#c084fc", mark: "GOG" },
    LaunchBox: { bg: "#1a1a1a", fg: "#999999", mark: "LB" },
    PlayStation: { bg: "#0a1a3d", fg: "#60a5fa", mark: "PS" },
    HowLongToBeat: { bg: "#1f1f1f", fg: "#d1d5db", mark: "HL" },
  };

  // which cards are expanded to show their configure form, collapsed by
  // default so the grid stays a dense, scannable wall of tiles
  const expanded = reactive<Record<string, boolean>>({});
  function toggleExpanded(key: string) {
    expanded[key] = !expanded[key];
  }

  const steamgriddbApiKey = ref(currentUser.value?.steamgriddb_api_key ?? "");
  const saving = ref(false);
  const saveError = ref<string | null>(null);
  const saveSuccess = ref(false);

  async function saveSteamgriddbKey() {
    saving.value = true;
    saveError.value = null;
    saveSuccess.value = false;

    try {
      await updateProfile({
        steamgriddbApiKey: steamgriddbApiKey.value.trim(),
      });
      await checkAuth();
      saveSuccess.value = true;
    } catch (err) {
      saveError.value =
        err instanceof Error ? err.message : "Failed to save settings";
    } finally {
      saving.value = false;
    }
  }

  // IGDB, deployment-wide, admin-only credentials (not per-user, see
  // database/models/app_integration_settings.py). Non-admins never see the
  // form, only whether it's configured.
  const isAdmin = ref(currentUser.value?.is_admin ?? false);
  const igdbClientId = ref("");
  const igdbClientSecret = ref("");
  const igdbConfigured = ref(false);
  const igdbLoading = ref(true);
  const igdbSaving = ref(false);
  const igdbError = ref<string | null>(null);

  const tmdbApiKey = ref("");
  const tmdbConfigured = ref(false);
  const tmdbSaving = ref(false);
  const tmdbError = ref<string | null>(null);

  const omdbApiKey = ref("");
  const omdbConfigured = ref(false);
  const omdbSaving = ref(false);
  const omdbError = ref<string | null>(null);

  // a key the server's environment provides is in effect, but Settings can
  // only override it, not clear it
  const keySources = ref<Record<string, string>>({});
  function keyPlaceholder(name: string, configured: boolean, empty: string) {
    if (!configured) return empty;
    return keySources.value[name] === "environment"
      ? "Set by the server: type a key to override it"
      : "Saved: leave blank to keep";
  }

  const tvdbApiKey = ref("");
  const tvdbConfigured = ref(false);
  const tvdbSaving = ref(false);
  const tvdbError = ref<string | null>(null);

  onMounted(async () => {
    if (!isAdmin.value) {
      igdbLoading.value = false;
      return;
    }
    try {
      const result = await fetchAppIntegrations();
      igdbClientId.value = result.igdb_client_id ?? "";
      igdbConfigured.value = result.igdb_configured;
      keySources.value = result.sources ?? {};
      tmdbConfigured.value = result.tmdb_configured;
      omdbConfigured.value = result.omdb_configured;
      tvdbConfigured.value = result.tvdb_configured;
      credentialStatus.TMDB = {
        status: tmdbConfigured.value ? "configured" : "not_configured",
      };
      credentialStatus.OMDb = {
        status: omdbConfigured.value ? "configured" : "not_configured",
      };
      credentialStatus.TVDB = {
        status: tvdbConfigured.value ? "configured" : "not_configured",
      };
    } finally {
      igdbLoading.value = false;
    }
  });

  async function saveIgdbCredentials() {
    igdbSaving.value = true;
    igdbError.value = null;
    try {
      const payload: { igdb_client_id?: string; igdb_client_secret?: string } =
        {
          igdb_client_id: igdbClientId.value.trim(),
        };
      if (igdbClientSecret.value.trim())
        payload.igdb_client_secret = igdbClientSecret.value.trim();
      const result = await updateAppIntegrations(payload);
      igdbClientId.value = result.igdb_client_id ?? "";
      igdbConfigured.value = result.igdb_configured;
      igdbClientSecret.value = "";
      credentialStatus.IGDB = {
        status: igdbConfigured.value ? "configured" : "not_configured",
      };
    } catch (err) {
      igdbError.value =
        err instanceof Error ? err.message : "Failed to save IGDB credentials";
    } finally {
      igdbSaving.value = false;
    }
  }

  async function clearIgdbCredentials() {
    igdbSaving.value = true;
    igdbError.value = null;
    try {
      const result = await updateAppIntegrations({
        igdb_client_id: "",
        igdb_client_secret: "",
      });
      keySources.value = result.sources ?? {};
      igdbClientId.value = result.igdb_client_id ?? "";
      igdbClientSecret.value = "";
      igdbConfigured.value = result.igdb_configured;
      credentialStatus.IGDB = {
        status: igdbConfigured.value ? "configured" : "not_configured",
      };
    } catch (err) {
      igdbError.value =
        err instanceof Error ? err.message : "Failed to clear IGDB credentials";
    } finally {
      igdbSaving.value = false;
    }
  }

  // TMDB/OMDb each save/clear only their own field via PUT — unlike IGDB's
  // DELETE above, which clears every app-integration field at once. Reusing
  // that same DELETE for a single-key provider would wipe the other two
  // providers' keys too, so a plain PUT with an empty string is used to
  // clear just one field instead.
  async function saveTmdbKey() {
    tmdbSaving.value = true;
    tmdbError.value = null;
    try {
      const result = await updateAppIntegrations({
        tmdb_api_key: tmdbApiKey.value.trim(),
      });
      tmdbConfigured.value = result.tmdb_configured;
      tmdbApiKey.value = "";
      credentialStatus.TMDB = {
        status: tmdbConfigured.value ? "configured" : "not_configured",
      };
    } catch (err) {
      tmdbError.value =
        err instanceof Error ? err.message : "Failed to save TMDB key";
    } finally {
      tmdbSaving.value = false;
    }
  }

  async function clearTmdbKey() {
    tmdbSaving.value = true;
    tmdbError.value = null;
    try {
      const result = await updateAppIntegrations({ tmdb_api_key: "" });
      tmdbApiKey.value = "";
      keySources.value = result.sources ?? {};
      tmdbConfigured.value = result.tmdb_configured;
      credentialStatus.TMDB = {
        status: tmdbConfigured.value ? "configured" : "not_configured",
      };
    } catch (err) {
      tmdbError.value =
        err instanceof Error ? err.message : "Failed to clear TMDB key";
    } finally {
      tmdbSaving.value = false;
    }
  }

  async function saveOmdbKey() {
    omdbSaving.value = true;
    omdbError.value = null;
    try {
      const result = await updateAppIntegrations({
        omdb_api_key: omdbApiKey.value.trim(),
      });
      omdbConfigured.value = result.omdb_configured;
      omdbApiKey.value = "";
      credentialStatus.OMDb = {
        status: omdbConfigured.value ? "configured" : "not_configured",
      };
    } catch (err) {
      omdbError.value =
        err instanceof Error ? err.message : "Failed to save OMDb key";
    } finally {
      omdbSaving.value = false;
    }
  }

  async function clearOmdbKey() {
    omdbSaving.value = true;
    omdbError.value = null;
    try {
      const result = await updateAppIntegrations({ omdb_api_key: "" });
      omdbApiKey.value = "";
      keySources.value = result.sources ?? {};
      omdbConfigured.value = result.omdb_configured;
      credentialStatus.OMDb = {
        status: omdbConfigured.value ? "configured" : "not_configured",
      };
    } catch (err) {
      omdbError.value =
        err instanceof Error ? err.message : "Failed to clear OMDb key";
    } finally {
      omdbSaving.value = false;
    }
  }

  async function saveTvdbKey() {
    tvdbSaving.value = true;
    tvdbError.value = null;
    try {
      const result = await updateAppIntegrations({
        tvdb_api_key: tvdbApiKey.value.trim(),
      });
      tvdbConfigured.value = result.tvdb_configured;
      tvdbApiKey.value = "";
      credentialStatus.TVDB = {
        status: tvdbConfigured.value ? "configured" : "not_configured",
      };
    } catch (err) {
      tvdbError.value =
        err instanceof Error ? err.message : "Failed to save TVDB key";
    } finally {
      tvdbSaving.value = false;
    }
  }

  async function clearTvdbKey() {
    tvdbSaving.value = true;
    tvdbError.value = null;
    try {
      const result = await updateAppIntegrations({ tvdb_api_key: "" });
      tvdbApiKey.value = "";
      keySources.value = result.sources ?? {};
      tvdbConfigured.value = result.tvdb_configured;
      credentialStatus.TVDB = {
        status: tvdbConfigured.value ? "configured" : "not_configured",
      };
    } catch (err) {
      tvdbError.value =
        err instanceof Error ? err.message : "Failed to clear TVDB key";
    } finally {
      tvdbSaving.value = false;
    }
  }

  const psnStatus = ref<PsnStatus>({ connected: false, validated_at: null });
  const psnLoading = ref(true);
  const npssoToken = ref("");
  const psnConnecting = ref(false);
  const psnError = ref<string | null>(null);
  const showDisconnectConfirm = ref(false);

  onMounted(async () => {
    try {
      psnStatus.value = await fetchPsnStatus();
    } finally {
      psnLoading.value = false;
    }
  });

  async function handleConnectPsn() {
    if (!npssoToken.value.trim()) {
      psnError.value = "Paste your npsso token first.";
      return;
    }
    psnConnecting.value = true;
    psnError.value = null;
    try {
      psnStatus.value = await connectPsn(npssoToken.value.trim());
      npssoToken.value = "";
    } catch (err) {
      psnError.value =
        err instanceof Error
          ? err.message
          : "Failed to connect PlayStation account";
    } finally {
      psnConnecting.value = false;
    }
  }

  async function confirmDisconnectPsn() {
    showDisconnectConfirm.value = false;
    psnError.value = null;
    try {
      await disconnectPsn();
      psnStatus.value = { connected: false, validated_at: null };
    } catch (err) {
      psnError.value =
        err instanceof Error
          ? err.message
          : "Failed to disconnect PlayStation account";
    }
  }

  // --- data-driven providers ---------------------------------------------

  interface ProviderFieldConfig {
    key: string;
    label: string;
    type: "text" | "password";
  }

  interface ProviderCardConfig {
    key: string;
    label: string;
    description: string;
    fields: ProviderFieldConfig[];
    kind: "wired" | "deferred";
    linkLabel?: string;
    linkUrl?: string;
  }

  const PROVIDER_CARDS: Record<string, ProviderCardConfig> = {
    Steam: {
      key: "Steam",
      label: "Steam",
      description:
        "No account needed for metadata search. Importing your library and achievements requires both fields below: your profile ID (the part after steamcommunity.com/id/, not the full link) and a Web API key. Your profile's game details must also be set to Public, or Steam silently returns an empty library.",
      fields: [
        { key: "steam_id", label: "Profile ID", type: "text" },
        { key: "api_key", label: "Web API Key", type: "password" },
      ],
      kind: "wired",
      linkLabel: "Get a Steam Web API key",
      linkUrl: "https://steamcommunity.com/dev/apikey",
    },
    IGDB: {
      key: "IGDB",
      label: "IGDB",
      description:
        "General game metadata and cover art. Uses one deployment-wide developer credential, managed by a server administrator here rather than per-user.",
      fields: [],
      kind: "wired",
    },
    TMDB: {
      key: "TMDB",
      label: "TMDB",
      description:
        "Movie metadata and poster art. Uses one deployment-wide API key, managed by a server administrator here rather than per-user.",
      fields: [],
      kind: "wired",
    },
    OMDb: {
      key: "OMDb",
      label: "OMDb",
      description:
        "IMDb-backed movie metadata, used alongside TMDB so a search still returns results if one source is down or missing a title. Uses one deployment-wide API key, managed by a server administrator here rather than per-user.",
      fields: [],
      kind: "wired",
    },
    TVDB: {
      key: "TVDB",
      label: "TheTVDB",
      description:
        "The only real franchise/relations source for TV shows (TMDB has no collection concept outside of movies). It powers the Related tab on a show's page. Uses one deployment-wide API key, managed by a server administrator here rather than per-user.",
      fields: [],
      kind: "wired",
    },
    RetroAchievements: {
      key: "RetroAchievements",
      label: "RetroAchievements",
      description:
        "Retro/console game metadata, plus your username to pull your library and unlocked achievements: powers all three from one key.",
      fields: [
        { key: "username", label: "Username", type: "text" },
        { key: "api_key", label: "API Key", type: "password" },
      ],
      kind: "wired",
      linkLabel: "Get a free key from RetroAchievements",
      linkUrl: "https://retroachievements.org/controlpanel.php",
    },
    GiantBomb: {
      key: "GiantBomb",
      label: "Giant Bomb",
      description: "General game metadata and cover art.",
      fields: [{ key: "api_key", label: "API Key", type: "password" }],
      kind: "wired",
      linkLabel: "Get a free key from Giant Bomb",
      linkUrl: "https://www.giantbomb.com/api/",
    },
    ScreenScraper: {
      key: "ScreenScraper",
      label: "ScreenScraper",
      description:
        "Retro box art and screenshots. Needs your personal screenscraper.fr account on top of the app-wide developer credentials your server administrator configures.",
      fields: [
        { key: "ssid", label: "Username", type: "text" },
        { key: "sspassword", label: "Password", type: "password" },
      ],
      kind: "wired",
      linkLabel: "Create a free ScreenScraper account",
      linkUrl: "https://www.screenscraper.fr/membreinscription.php",
    },
    Xbox: {
      key: "Xbox",
      label: "Xbox",
      description:
        "Unofficial: Xbox's real API needs a full sign-in flow this page can't host yet. Saving your Azure app credentials here just gets them ready for that; nothing is pulled from Xbox yet.",
      fields: [
        { key: "client_id", label: "Application (client) ID", type: "text" },
        { key: "client_secret", label: "Client secret", type: "password" },
      ],
      kind: "deferred",
    },
    GOG: {
      key: "GOG",
      label: "GOG",
      description:
        "Metadata search uses GOG's public store catalog: no key needed. The refresh token below is only for a future library import, not search.",
      fields: [
        {
          key: "refresh_token",
          label: "Refresh token (library import only)",
          type: "password",
        },
      ],
      kind: "wired",
    },
  };

  const credentialStatus = reactive<Record<string, ProviderCredentialStatus>>(
    {},
  );
  const fieldValues = reactive<Record<string, Record<string, string>>>({});
  const cardSaving = reactive<Record<string, boolean>>({});
  const cardError = reactive<Record<string, string | null>>({});
  const cardInfo = reactive<Record<string, string | null>>({});
  const credentialsLoading = ref(true);

  // must be ready before first render, the template binds
  // fieldValues[card.key][field.key] immediately, not just after mount
  for (const key of Object.keys(PROVIDER_CARDS)) {
    fieldValues[key] = {};
  }

  onMounted(async () => {
    try {
      const result = await fetchProviderCredentials();
      Object.assign(credentialStatus, result);
      // prefill non-secret fields (profile IDs, usernames) that are already
      // saved, so the form shows them filled instead of misleadingly blank
      for (const [key, status] of Object.entries(result)) {
        if (status.fields)
          Object.assign(
            fieldValues[key] ?? (fieldValues[key] = {}),
            status.fields,
          );
      }
    } finally {
      credentialsLoading.value = false;
    }
  });

  // a password-type field that's already saved gets a placeholder instead of
  // its real value (never echoed back), still communicates "this is filled"
  function passwordPlaceholder(
    key: string,
    fieldKey: string,
    label: string,
  ): string {
    const status = credentialStatus[key]?.status;
    const alreadySaved =
      status === "connected" || status === "saved" || status === "configured";
    if (alreadySaved && !fieldValues[key]?.[fieldKey])
      return "Already saved: paste a new value to replace it";
    return `Paste your ${label.toLowerCase()}`;
  }

  // no personal key, but the server's own key covers searches (#234)
  function usesServerKey(key: string): boolean {
    const entry = credentialStatus[key];
    return entry?.status === "not_configured" && !!entry.server_configured;
  }

  function statusLabel(key: string): string {
    const status = credentialStatus[key]?.status;
    if (status === "connected") return "Connected";
    if (status === "saved" || status === "configured") return "Saved";
    if (status === "error") return "Error";
    if (usesServerKey(key)) return "Using server key";
    return "Not configured";
  }
  function statusClass(key: string): string {
    const status = credentialStatus[key]?.status;
    if (status === "connected") return "connected";
    if (status === "saved" || status === "configured") return "saved";
    if (status === "error") return "error";
    if (usesServerKey(key)) return "saved";
    return "disconnected";
  }

  async function saveCard(card: ProviderCardConfig) {
    cardSaving[card.key] = true;
    cardError[card.key] = null;
    cardInfo[card.key] = null;
    try {
      const result = await saveProviderCredentials(
        card.key,
        fieldValues[card.key],
      );
      credentialStatus[card.key] = result;
      if (result.status === "error") {
        cardError[card.key] =
          result.detail ?? "Could not verify these credentials.";
      } else if (result.status === "saved" && result.detail) {
        cardInfo[card.key] = result.detail;
      }
    } catch (err) {
      cardError[card.key] =
        err instanceof Error ? err.message : "Failed to save";
    } finally {
      cardSaving[card.key] = false;
    }
  }

  async function clearCard(card: ProviderCardConfig) {
    try {
      await deleteProviderCredentials(card.key);
      credentialStatus[card.key] = { status: "not_configured" };
      cardError[card.key] = null;
      fieldValues[card.key] = {};
    } catch (err) {
      cardError[card.key] =
        err instanceof Error ? err.message : "Failed to disconnect";
    }
  }

  // --- library sync (real owned-games + achievements pull) ---------------

  const librarySyncing = reactive<Record<LibrarySyncProvider, boolean>>({
    steam: false,
    psn: false,
    retroachievements: false,
  });
  const LIBRARY_SYNC_LABELS: Record<LibrarySyncProvider, string> = {
    steam: "Steam",
    psn: "PlayStation",
    retroachievements: "RetroAchievements",
  };

  async function handleSyncLibrary(provider: LibrarySyncProvider) {
    librarySyncing[provider] = true;
    // indeterminate, the backend is one all-at-once request with no
    // per-game signal until it resolves, so there's nothing real to show as
    // a fraction while it's in flight
    const taskId = startTask(
      `Syncing ${LIBRARY_SYNC_LABELS[provider]} library`,
      1,
      { indeterminate: true },
    );
    try {
      const result = await syncLibrary(provider);
      completeTask(
        taskId,
        `${result.games_added} added, ${result.games_updated} updated, ${result.achievements_synced} achievements`,
      );
      // the request itself wasn't live, but revealing the touched titles one
      // at a time still reads as a real "feed" once the result is in
      for (const [i, title] of result.games.entries()) {
        setTimeout(() => addFeedItem(taskId, title), i * 90);
      }
      // refresh the persistent "N games, last synced ..." line so it reflects
      // this run immediately instead of only on the next page load
      Object.assign(credentialStatus, await fetchProviderCredentials());
    } catch (err) {
      errorTask(taskId, err instanceof Error ? err.message : "Sync failed");
    } finally {
      librarySyncing[provider] = false;
    }
  }

  // only claims "synced" once a library sync has actually run, a game
  // count alone (e.g. from manually-added Steam games) doesn't mean that
  function formatLastSynced(
    status: ProviderCredentialStatus | undefined,
  ): string | null {
    if (!status?.last_synced_at) return null;
    const when = new Date(status.last_synced_at * 1000).toLocaleString(
      undefined,
      {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      },
    );
    const count = status.library_games ?? 0;
    return `${count} game${count === 1 ? "" : "s"} · synced ${when}`;
  }

  // HowLongToBeat, a real toggle now, not just informational. "Enabled"
  // means "HowLongToBeat" is present in the user's scan provider_order.
  const hltbEnabled = ref(false);
  const hltbLoading = ref(true);
  const hltbSaving = ref(false);
  const hltbError = ref<string | null>(null);

  onMounted(async () => {
    try {
      const scan = await fetchScanSettings();
      hltbEnabled.value = scan.provider_order.includes("HowLongToBeat");
    } finally {
      hltbLoading.value = false;
    }
  });

  async function toggleHltb(enabled: boolean) {
    hltbSaving.value = true;
    hltbError.value = null;
    try {
      const scan = await fetchScanSettings();
      const nextOrder = enabled
        ? [
            ...scan.provider_order.filter((p) => p !== "HowLongToBeat"),
            "HowLongToBeat",
          ]
        : scan.provider_order.filter((p) => p !== "HowLongToBeat");
      await updateScanSettings({
        provider_order: nextOrder as typeof scan.provider_order,
      });
      hltbEnabled.value = enabled;
    } catch (err) {
      hltbError.value =
        err instanceof Error ? err.message : "Failed to update HowLongToBeat";
    } finally {
      hltbSaving.value = false;
    }
  }

  return {
    SHORT_DESC,
    VISUALS,
    expanded,
    toggleExpanded,
    steamgriddbApiKey,
    saving,
    saveError,
    saveSuccess,
    saveSteamgriddbKey,
    isAdmin,
    igdbClientId,
    igdbClientSecret,
    igdbConfigured,
    igdbSaving,
    igdbError,
    tmdbApiKey,
    tmdbConfigured,
    tmdbSaving,
    tmdbError,
    omdbApiKey,
    omdbConfigured,
    omdbSaving,
    omdbError,
    keyPlaceholder,
    tvdbApiKey,
    tvdbConfigured,
    tvdbSaving,
    tvdbError,
    saveIgdbCredentials,
    clearIgdbCredentials,
    saveTmdbKey,
    clearTmdbKey,
    saveOmdbKey,
    clearOmdbKey,
    saveTvdbKey,
    clearTvdbKey,
    psnStatus,
    psnLoading,
    npssoToken,
    psnConnecting,
    psnError,
    showDisconnectConfirm,
    handleConnectPsn,
    confirmDisconnectPsn,
    PROVIDER_CARDS,
    credentialStatus,
    fieldValues,
    cardSaving,
    cardError,
    cardInfo,
    credentialsLoading,
    passwordPlaceholder,
    statusLabel,
    statusClass,
    saveCard,
    clearCard,
    librarySyncing,
    handleSyncLibrary,
    formatLastSynced,
    hltbEnabled,
    hltbLoading,
    hltbSaving,
    hltbError,
    toggleHltb,
  };
}
