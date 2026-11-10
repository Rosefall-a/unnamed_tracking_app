// strictly separated, a data provider never contributes art and an image
// provider never contributes data (see backend search.py)
export type DataProvider =
  | "Steam"
  | "IGDB"
  | "RetroAchievements"
  | "GiantBomb"
  | "GOG"
  | "HowLongToBeat";
export type ImageProvider = "SteamGridDB" | "ScreenScraper";
export type ScanProvider = DataProvider | ImageProvider;

export interface ScanSettings {
  id: string;
  user_id: string;
  provider_order: DataProvider[];
  image_provider_order: ImageProvider[];
  save_developer: boolean;
  save_publisher: boolean;
  save_series: boolean;
  save_tags: boolean;
  save_features: boolean;
  save_description: boolean;
  save_age_rating: boolean;
  save_release_date: boolean;
  save_time_to_beat: boolean;
  save_key_art: boolean;
  save_banner: boolean;
  save_logo: boolean;
  save_icon: boolean;
  // a sync removes achievements a game no longer has
  remove_gone_achievements: boolean;
  // {provider name: epoch seconds}, last time that provider actually
  // returned a result during a search; read-only, not part of ScanSettingsUpdate
  provider_last_used: Record<string, number>;
  created_at: number;
  updated_at: number;
}

export type ScanSettingsUpdate = Partial<
  Pick<
    ScanSettings,
    | "provider_order"
    | "image_provider_order"
    | "save_developer"
    | "save_publisher"
    | "save_series"
    | "save_tags"
    | "save_features"
    | "save_description"
    | "save_age_rating"
    | "save_release_date"
    | "save_time_to_beat"
    | "save_key_art"
    | "save_banner"
    | "save_logo"
    | "save_icon"
    | "remove_gone_achievements"
  >
>;

const MOCK_SCAN_SETTINGS: ScanSettings = {
  id: "mock",
  user_id: "mock",
  provider_order: [
    "IGDB",
    "GiantBomb",
    "GOG",
    "Steam",
    "RetroAchievements",
    "HowLongToBeat",
  ],
  image_provider_order: ["SteamGridDB", "ScreenScraper"],
  save_developer: true,
  save_publisher: true,
  save_series: true,
  save_tags: true,
  save_features: true,
  save_description: true,
  save_age_rating: true,
  save_release_date: true,
  save_time_to_beat: true,
  save_key_art: true,
  save_banner: true,
  save_logo: true,
  save_icon: true,
  remove_gone_achievements: true,
  provider_last_used: {},
  created_at: 0,
  updated_at: 0,
};

export async function fetchScanSettings(): Promise<ScanSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return { ...MOCK_SCAN_SETTINGS };
  }

  const response = await fetch("/api/settings/scan", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(
      `Could not fetch scan settings: ${response.status} ${response.statusText}`,
    );
  }
  return await response.json();
}

export async function updateScanSettings(
  payload: ScanSettingsUpdate,
): Promise<ScanSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    Object.assign(MOCK_SCAN_SETTINGS, payload);
    return { ...MOCK_SCAN_SETTINGS };
  }

  const response = await fetch("/api/settings/scan", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Could not update scan settings: ${response.status} ${response.statusText} ${message}`,
    );
  }
  return await response.json();
}

export interface UploadLimits {
  max_upload_size_mb: number;
  // set by MAX_UPLOAD_SIZE_MB on the server, so it cannot be changed here
  from_environment: boolean;
  max_clip_size_mb: number;
  max_save_size_mb: number;
  max_world_save_size_mb: number;
}

export async function fetchUploadLimits(): Promise<UploadLimits> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return {
      max_upload_size_mb: 15,
      from_environment: false,
      max_clip_size_mb: 500,
      max_save_size_mb: 4096,
      max_world_save_size_mb: 2000,
    };
  }

  const response = await fetch("/api/settings/upload-limits", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(
      `Could not fetch upload limits: ${response.status} ${response.statusText}`,
    );
  }
  return await response.json();
}

// Admin-only: overrides MAX_UPLOAD_SIZE_MB without touching the server's
// environment. `null` clears the override and goes back to that default.
export async function updateUploadLimit(
  maxUploadSizeMb: number | null,
): Promise<{ max_upload_size_mb: number }> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return { max_upload_size_mb: maxUploadSizeMb ?? 15 };
  }

  const response = await fetch("/api/settings/upload-limit", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ max_upload_size_mb: maxUploadSizeMb }),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Could not update the upload limit: ${response.status} ${response.statusText} ${message}`,
    );
  }
  return await response.json();
}

export interface SystemInfo {
  server_time: number;
  uptime_seconds: number;
  debug: boolean;
  python_version: string;
  platform: string;
}

// Admin-only, for Settings > Administration > Dev Tools.
export async function fetchSystemInfo(): Promise<SystemInfo> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return {
      server_time: Math.floor(Date.now() / 1000),
      uptime_seconds: 3600,
      debug: false,
      python_version: "3.12.0",
      platform: "Mock-Platform",
    };
  }

  const response = await fetch("/api/settings/system-info", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(
      `Could not fetch system info: ${response.status} ${response.statusText}`,
    );
  }
  return await response.json();
}

export interface ProviderCredentialStatus {
  status: "not_configured" | "configured" | "connected" | "saved" | "error";
  detail?: string | null;
  app_configured?: boolean;
  // a server-wide key (Server Integrations or the environment) covers this
  // provider for anyone without their own
  server_configured?: boolean;
  // library-sync providers only (Steam, RetroAchievements, PlayStation)
  library_games?: number;
  last_synced_at?: number | null;
  // who's connected, when known (Steam, RetroAchievements, PlayStation)
  display_name?: string | null;
  avatar_url?: string | null;
  // non-secret field values already saved (steam_id, username, ssid,
  // client_id) so the form can show them filled instead of blank
  fields?: Record<string, string>;
}

const MOCK_PROVIDER_CREDENTIALS: Record<string, ProviderCredentialStatus> = {};

export async function fetchProviderCredentials(): Promise<
  Record<string, ProviderCredentialStatus>
> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return { ...MOCK_PROVIDER_CREDENTIALS };
  }

  const response = await fetch("/api/settings/provider-credentials", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(
      `Could not fetch provider credentials: ${response.status} ${response.statusText}`,
    );
  }
  return await response.json();
}

export async function saveProviderCredentials(
  provider: string,
  fields: Record<string, string>,
): Promise<ProviderCredentialStatus> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    const result: ProviderCredentialStatus = { status: "connected" };
    MOCK_PROVIDER_CREDENTIALS[provider] = { status: "configured" };
    return result;
  }

  const response = await fetch(
    `/api/settings/provider-credentials/${encodeURIComponent(provider)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ fields }),
    },
  );
  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Could not save ${provider} credentials: ${response.status} ${response.statusText} ${message}`,
    );
  }
  return await response.json();
}

export async function deleteProviderCredentials(
  provider: string,
): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    delete MOCK_PROVIDER_CREDENTIALS[provider];
    return;
  }

  const response = await fetch(
    `/api/settings/provider-credentials/${encodeURIComponent(provider)}`,
    {
      method: "DELETE",
      credentials: "include",
    },
  );
  if (!response.ok) {
    throw new Error(
      `Could not disconnect ${provider}: ${response.status} ${response.statusText}`,
    );
  }
}

// Deployment-wide (not per-user) integration credentials, admin-only.
// An IGDB/Twitch developer app is registered once per self-hosted
// instance and entered here, not baked into .env, so a downloaded copy of
// this app never ships with someone else's credentials.
export interface AppIntegrationSettings {
  igdb_client_id: string | null;
  igdb_configured: boolean;
  tmdb_configured: boolean;
  omdb_configured: boolean;
  tvdb_configured: boolean;
  // where each key in effect comes from: Settings, or the server environment
  sources?: Record<string, "database" | "environment">;
}

export async function fetchAppIntegrations(): Promise<AppIntegrationSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return {
      igdb_client_id: null,
      igdb_configured: false,
      tmdb_configured: false,
      omdb_configured: false,
      tvdb_configured: false,
    };
  }
  const response = await fetch("/api/settings/app-integrations", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(
      `Could not fetch app integrations: ${response.status} ${response.statusText}`,
    );
  }
  return await response.json();
}

export async function updateAppIntegrations(payload: {
  igdb_client_id?: string;
  igdb_client_secret?: string;
  tmdb_api_key?: string;
  omdb_api_key?: string;
  tvdb_api_key?: string;
}): Promise<AppIntegrationSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return {
      igdb_client_id: payload.igdb_client_id ?? null,
      igdb_configured: true,
      tmdb_configured: !!payload.tmdb_api_key,
      omdb_configured: !!payload.omdb_api_key,
      tvdb_configured: !!payload.tvdb_api_key,
    };
  }
  const response = await fetch("/api/settings/app-integrations", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Could not save app integrations: ${response.status} ${response.statusText} ${message}`,
    );
  }
  return await response.json();
}

export interface MediaRefreshProgress {
  running: boolean;
  mode: "needed" | "all";
  phase: string;
  total: number;
  done: number;
  current: string;
  checked: number;
  skippedUpToDate: number;
  animeEpisodesAdded: number;
  animeEpisodesUpdated: number;
  tvEpisodesAdded: number;
  tvEpisodesUpdated: number;
  countsFixed: number;
  animeMetadataHealed: number;
  unreachable: string[];
  startedAt: number | null;
  finishedAt: number | null;
  error: string | null;
}

interface BackendRefreshProgress {
  running: boolean;
  mode: "needed" | "all";
  phase: string;
  total: number;
  done: number;
  current: string;
  checked: number;
  skipped_up_to_date: number;
  anime_episodes_added: number;
  anime_episodes_updated: number;
  tv_episodes_added: number;
  tv_episodes_updated: number;
  counts_fixed: number;
  anime_metadata_healed: number;
  unreachable: string[];
  started_at: number | null;
  finished_at: number | null;
  error: string | null;
}

function mapRefreshProgress(d: BackendRefreshProgress): MediaRefreshProgress {
  return {
    running: d.running,
    mode: d.mode,
    phase: d.phase,
    total: d.total,
    done: d.done,
    current: d.current,
    checked: d.checked,
    skippedUpToDate: d.skipped_up_to_date,
    animeEpisodesAdded: d.anime_episodes_added,
    animeEpisodesUpdated: d.anime_episodes_updated,
    tvEpisodesAdded: d.tv_episodes_added,
    tvEpisodesUpdated: d.tv_episodes_updated,
    countsFixed: d.counts_fixed,
    animeMetadataHealed: d.anime_metadata_healed,
    unreachable: d.unreachable,
    startedAt: d.started_at,
    finishedAt: d.finished_at,
    error: d.error,
  };
}

// Starts the episode refresh in the background and returns at once; poll
// fetchMediaRefreshProgress for how far it has got. "needed" only touches
// titles that need it, "all" checks every title.
export async function startMediaRefresh(
  mode: "needed" | "all",
): Promise<MediaRefreshProgress> {
  const response = await fetch(
    `/api/settings/refresh-media-metadata?mode=${mode}`,
    { method: "POST", credentials: "include" },
  );
  if (!response.ok) {
    throw new Error(`Could not start the refresh: ${response.status}`);
  }
  return mapRefreshProgress(await response.json());
}

export async function fetchMediaRefreshProgress(): Promise<MediaRefreshProgress> {
  const response = await fetch("/api/settings/refresh-media-progress", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Could not read the refresh progress: ${response.status}`);
  }
  return mapRefreshProgress(await response.json());
}

// Jobs the app runs on a schedule (see backend features/jobs.py). The airing
// check starts on, the heavy media refresh starts off.
export interface CleanupJob {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  intervalMinutes: number;
  minIntervalMinutes: number;
  maxIntervalMinutes: number;
  lastRunAt: number | null;
  lastSummary: string;
  lastResult: Record<string, number | string | boolean | null>;
  running: boolean;
}
interface BackendJob {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  interval_minutes: number;
  min_interval_minutes: number;
  max_interval_minutes: number;
  last_run_at: number | null;
  last_summary: string;
  last_result: Record<string, number | string | boolean | null>;
  running: boolean;
}
function mapJob(j: BackendJob): CleanupJob {
  return {
    id: j.id,
    name: j.name,
    description: j.description,
    enabled: j.enabled,
    intervalMinutes: j.interval_minutes,
    minIntervalMinutes: j.min_interval_minutes,
    maxIntervalMinutes: j.max_interval_minutes,
    lastRunAt: j.last_run_at,
    lastSummary: j.last_summary,
    lastResult: j.last_result,
    running: j.running,
  };
}
export async function fetchJobs(): Promise<CleanupJob[]> {
  const response = await fetch("/api/settings/jobs", {
    credentials: "include",
  });
  if (!response.ok)
    throw new Error(`Could not load the jobs: ${response.status}`);
  return ((await response.json()) as BackendJob[]).map(mapJob);
}
export async function updateJob(
  id: string,
  changes: { enabled?: boolean; intervalMinutes?: number },
): Promise<CleanupJob> {
  const response = await fetch(`/api/settings/jobs/${id}`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      enabled: changes.enabled,
      interval_minutes: changes.intervalMinutes,
    }),
  });
  if (!response.ok)
    throw new Error(`Could not save the job: ${response.status}`);
  return mapJob(await response.json());
}
export async function runJobNow(id: string): Promise<void> {
  const response = await fetch(`/api/settings/jobs/${id}/run`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok)
    throw new Error(`Could not start the job: ${response.status}`);
}

// Settings > Administration > Backups (see backend api/routes/backups.py).
export interface BackupFile {
  name: string;
  createdAt: number;
  size: number;
  items: number | null;
  tables: number | null;
  // the copy of everyone's files made with it, when there is one
  files: { size: number; count: number; skipped: number } | null;
}
// which disk a folder is on, as the server sees it
export interface BackupDrive {
  label: string;
  // false: only inside the container, gone when it is removed
  mounted: boolean;
}
export interface BackupStorage {
  backups: BackupDrive | null;
  data: BackupDrive | null;
  sameDrive: boolean | null;
}
export interface BackupOverview {
  enabled: boolean;
  intervalMinutes: number;
  minIntervalMinutes: number;
  maxIntervalMinutes: number;
  keep: number;
  maxKeep: number;
  lastRunAt: number | null;
  lastResult: Record<string, number | string | boolean | null>;
  running: boolean;
  folder: string;
  includeFiles: boolean;
  filesKeep: number;
  maxFilesKeep: number;
  storage: BackupStorage;
  backups: BackupFile[];
}
export interface Leftover {
  kind: "game_trash" | "account_files" | "deleted_account" | "old_backups";
  name: string;
  label: string;
  bytes: number;
  modifiedAt: number;
}
interface BackendBackupFile {
  name: string;
  created_at: number;
  size: number;
  items: number | null;
  tables: number | null;
  files?: { size: number; count: number; skipped: number } | null;
}
interface BackendDrive {
  label: string;
  mounted: boolean;
}
interface BackendBackupOverview {
  enabled: boolean;
  interval_minutes: number;
  min_interval_minutes: number;
  max_interval_minutes: number;
  keep: number;
  max_keep: number;
  last_run_at: number | null;
  last_result: Record<string, number | string | boolean | null>;
  running: boolean;
  folder: string;
  include_files?: boolean;
  files_keep?: number;
  max_files_keep?: number;
  storage?: {
    backups: BackendDrive | null;
    data: BackendDrive | null;
    same_drive: boolean | null;
  };
  backups?: BackendBackupFile[];
}
function mapBackupFile(f: BackendBackupFile): BackupFile {
  return {
    name: f.name,
    createdAt: f.created_at,
    size: f.size,
    items: f.items,
    tables: f.tables ?? null,
    files: f.files
      ? { size: f.files.size, count: f.files.count, skipped: f.files.skipped }
      : null,
  };
}
function mapBackupOverview(b: BackendBackupOverview): BackupOverview {
  return {
    enabled: b.enabled,
    intervalMinutes: b.interval_minutes,
    minIntervalMinutes: b.min_interval_minutes,
    maxIntervalMinutes: b.max_interval_minutes,
    keep: b.keep,
    maxKeep: b.max_keep,
    lastRunAt: b.last_run_at,
    lastResult: b.last_result,
    running: b.running,
    folder: b.folder,
    includeFiles: b.include_files ?? false,
    filesKeep: b.files_keep ?? 2,
    maxFilesKeep: b.max_files_keep ?? 30,
    storage: {
      backups: b.storage?.backups ?? null,
      data: b.storage?.data ?? null,
      sameDrive: b.storage?.same_drive ?? null,
    },
    backups: (b.backups ?? []).map(mapBackupFile),
  };
}
async function backupError(response: Response, fallback: string) {
  const body = await response.json().catch(() => null);
  return new Error(body?.detail ?? `${fallback}: ${response.status}`);
}
export async function fetchBackups(): Promise<BackupOverview> {
  const response = await fetch("/api/settings/backups", {
    credentials: "include",
  });
  if (!response.ok) throw await backupError(response, "Could not load backups");
  return mapBackupOverview(await response.json());
}
export async function updateBackupSettings(changes: {
  enabled?: boolean;
  intervalMinutes?: number;
  keep?: number;
  includeFiles?: boolean;
  filesKeep?: number;
}): Promise<BackupOverview> {
  const response = await fetch("/api/settings/backups", {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      enabled: changes.enabled,
      interval_minutes: changes.intervalMinutes,
      keep: changes.keep,
      include_files: changes.includeFiles,
      files_keep: changes.filesKeep,
    }),
  });
  if (!response.ok) throw await backupError(response, "Could not save");
  return mapBackupOverview(await response.json());
}
export async function runBackupsNow(): Promise<boolean> {
  const response = await fetch("/api/settings/backups/run", {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok)
    throw await backupError(response, "Could not start a backup");
  return (await response.json()).started as boolean;
}
export function backupDownloadUrl(name: string): string {
  return `/api/settings/backups/database/${encodeURIComponent(name)}`;
}
export function backupFilesDownloadUrl(name: string): string {
  return `${backupDownloadUrl(name)}/files`;
}
export async function deleteBackup(name: string): Promise<void> {
  const response = await fetch(backupDownloadUrl(name), {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok)
    throw await backupError(response, "Could not delete the backup");
}
export async function fetchLeftovers(): Promise<Leftover[]> {
  const response = await fetch("/api/settings/backups/leftovers", {
    credentials: "include",
  });
  if (!response.ok)
    throw await backupError(response, "Could not load leftover files");
  return (
    (await response.json()) as {
      kind: Leftover["kind"];
      name: string;
      label: string;
      bytes: number;
      modified_at: number;
    }[]
  ).map((l) => ({ ...l, modifiedAt: l.modified_at }));
}
export async function deleteLeftoversOfKind(
  kind: Leftover["kind"],
): Promise<number> {
  const response = await fetch(`/api/settings/backups/leftovers/${kind}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok)
    throw await backupError(response, "Could not delete the files");
  return ((await response.json()) as { deleted: number }).deleted;
}
export async function deleteLeftover(item: Leftover): Promise<void> {
  const response = await fetch(
    `/api/settings/backups/leftovers/${item.kind}/${encodeURIComponent(item.name)}`,
    { method: "DELETE", credentials: "include" },
  );
  if (!response.ok)
    throw await backupError(response, "Could not delete the files");
}
