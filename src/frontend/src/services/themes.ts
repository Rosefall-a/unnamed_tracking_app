import { failedRequest } from "./apiError";

export interface InstalledTheme {
  format_version: 1;
  id: string;
  name: string;
  version: string;
  publisher: string;
  description: string;
  kind: "official" | "example";
  stylesheet: string;
  supports: ("light" | "dark")[];
  digest: string;
  enabled: boolean;
}
export interface ThemeCatalogue {
  default_theme: string;
  themes: InstalledTheme[];
}
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/themes${path}`, {
    ...options,
    credentials: "include",
  });
  if (!response.ok) throw await failedRequest(response);
  return response.status === 204 ? (undefined as T) : response.json();
}
export function fetchThemes(administration = false): Promise<ThemeCatalogue> {
  return request(administration ? "/manage" : "");
}
export function uploadTheme(
  file: File,
  preview = false,
): Promise<InstalledTheme> {
  const body = new FormData();
  body.append("file", file);
  return request(preview ? "/install/preview" : "/install", {
    method: "POST",
    body,
  });
}
export function configureTheme(
  id: string,
  enabled: boolean,
): Promise<InstalledTheme> {
  return request(`/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
}
export function setDefaultTheme(
  id: string,
): Promise<{ default_theme: string }> {
  return request("/default", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ theme_id: id }),
  });
}
export function removeTheme(id: string): Promise<void> {
  return request(`/${encodeURIComponent(id)}`, { method: "DELETE" });
}
export function themeStylesheetUrl(theme: InstalledTheme): string {
  return `/api/themes/assets/${encodeURIComponent(theme.id)}/${encodeURIComponent(theme.digest)}/${theme.stylesheet.split("/").map(encodeURIComponent).join("/")}`;
}
export function resolveInstalledTheme(
  catalogue: ThemeCatalogue,
  selection: string,
  mode: "light" | "dark",
): InstalledTheme | undefined {
  const id = selection === "server" ? catalogue.default_theme : selection;
  return catalogue.themes.find(
    (theme) =>
      theme.id === id && theme.enabled && theme.supports.includes(mode),
  );
}
