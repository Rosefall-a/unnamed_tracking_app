// strictly separated, a data provider never contributes art and an image
// provider never contributes data (see backend search.py)
import { apiError } from "./apiErrors";

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
  id: string; user_id: string; provider_order: DataProvider[]; image_provider_order: ImageProvider[];
  save_developer: boolean; save_publisher: boolean; save_series: boolean; save_tags: boolean;
  save_features: boolean; save_description: boolean; save_age_rating: boolean; save_release_date: boolean;
  save_time_to_beat: boolean; save_key_art: boolean; save_banner: boolean; save_logo: boolean; save_icon: boolean;
  provider_last_used: Record<string, number>; created_at: number; updated_at: number;
}

export type ScanSettingsUpdate = Partial<Pick<ScanSettings,
  | "provider_order" | "image_provider_order" | "save_developer" | "save_publisher" | "save_series"
  | "save_tags" | "save_features" | "save_description" | "save_age_rating" | "save_release_date"
  | "save_time_to_beat" | "save_key_art" | "save_banner" | "save_logo" | "save_icon"
>>;

const MOCK_SCAN_SETTINGS: ScanSettings = {
  id: "mock", user_id: "mock",
  provider_order: ["IGDB", "GiantBomb", "GOG", "Steam", "RetroAchievements", "HowLongToBeat"],
  image_provider_order: ["SteamGridDB", "ScreenScraper"], save_developer: true, save_publisher: true,
  save_series: true, save_tags: true, save_features: true, save_description: true, save_age_rating: true,
  save_release_date: true, save_time_to_beat: true, save_key_art: true, save_banner: true, save_logo: true,
  save_icon: true, provider_last_used: {}, created_at: 0, updated_at: 0,
};

export async function fetchScanSettings(): Promise<ScanSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") return { ...MOCK_SCAN_SETTINGS };
  const response = await fetch("/api/settings/scan", { credentials: "include" });
  if (!response.ok) throw await apiError(response, "Failed to fetch scan settings");
  return await response.json();
}

export async function updateScanSettings(payload: ScanSettingsUpdate): Promise<ScanSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") { Object.assign(MOCK_SCAN_SETTINGS, payload); return { ...MOCK_SCAN_SETTINGS }; }
  const response = await fetch("/api/settings/scan", {
    method: "PUT", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(payload),
  });
  if (!response.ok) throw await apiError(response, "Failed to update scan settings");
  return await response.json();
}

export async function fetchUploadLimits(): Promise<{ max_upload_size_mb: number }> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") return { max_upload_size_mb: 15 };
  const response = await fetch("/api/settings/upload-limits", { credentials: "include" });
  if (!response.ok) throw await apiError(response, "Failed to fetch upload limits");
  return await response.json();
}

export interface ProviderCredentialStatus {
  status: "not_configured" | "configured" | "connected" | "saved" | "error";
  detail?: string | null; app_configured?: boolean; library_games?: number; last_synced_at?: number | null;
  display_name?: string | null; avatar_url?: string | null; fields?: Record<string, string>;
}
const MOCK_PROVIDER_CREDENTIALS: Record<string, ProviderCredentialStatus> = {};

export async function fetchProviderCredentials(): Promise<Record<string, ProviderCredentialStatus>> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") return { ...MOCK_PROVIDER_CREDENTIALS };
  const response = await fetch("/api/settings/provider-credentials", { credentials: "include" });
  if (!response.ok) throw await apiError(response, "Failed to fetch provider credentials");
  return await response.json();
}

export async function saveProviderCredentials(provider: string, fields: Record<string, string>): Promise<ProviderCredentialStatus> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    const result: ProviderCredentialStatus = { status: "connected" }; MOCK_PROVIDER_CREDENTIALS[provider] = { status: "configured" }; return result;
  }
  const response = await fetch(`/api/settings/provider-credentials/${encodeURIComponent(provider)}`, {
    method: "PUT", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify({ fields }),
  });
  if (!response.ok) throw await apiError(response, `Failed to save ${provider} credentials`);
  return await response.json();
}

export async function deleteProviderCredentials(provider: string): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") { delete MOCK_PROVIDER_CREDENTIALS[provider]; return; }
  const response = await fetch(`/api/settings/provider-credentials/${encodeURIComponent(provider)}`, { method: "DELETE", credentials: "include" });
  if (!response.ok) throw await apiError(response, `Failed to disconnect ${provider}`);
}

export interface AppIntegrationSettings { igdb_client_id: string | null; igdb_configured: boolean; }

export async function fetchAppIntegrations(): Promise<AppIntegrationSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") return { igdb_client_id: null, igdb_configured: false };
  const response = await fetch("/api/settings/app-integrations", { credentials: "include" });
  if (!response.ok) throw await apiError(response, "Failed to fetch app integrations");
  return await response.json();
}

export async function updateAppIntegrations(payload: { igdb_client_id?: string; igdb_client_secret?: string }): Promise<AppIntegrationSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") return { igdb_client_id: payload.igdb_client_id ?? null, igdb_configured: true };
  const response = await fetch("/api/settings/app-integrations", {
    method: "PUT", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(payload),
  });
  if (!response.ok) throw await apiError(response, "Failed to save app integrations");
  return await response.json();
}

export async function deleteAppIntegrations(): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") return;
  const response = await fetch("/api/settings/app-integrations", { method: "DELETE", credentials: "include" });
  if (!response.ok) throw await apiError(response, "Failed to clear app integrations");
}
