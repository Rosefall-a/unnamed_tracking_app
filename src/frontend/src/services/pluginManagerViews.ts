import type { PluginCatalogEntry, PluginSummary } from "./plugins";
export type ManagerView =
  | "Installed"
  | "Updates Available"
  | "Discover"
  | "Available to Install"
  | "All";
export function managerEntries(
  installed: PluginSummary[],
  catalogue: PluginCatalogEntry[],
  view: ManagerView,
  search = "",
  tag = "",
  channel = "",
): Array<PluginSummary | PluginCatalogEntry> {
  const ids = new Set(installed.map((item) => item.plugin_id));
  const sources = new Map<string, PluginCatalogEntry>();
  for (const item of catalogue) {
    if (!sources.has(item.plugin_id)) sources.set(item.plugin_id, item);
  }
  const available = [...sources.values()].filter(
    (item) => !ids.has(item.plugin_id),
  );
  const inventory = installed.map((item) => ({
    ...item,
    tags: [
      ...new Set([
        ...(item.tags ?? []),
        ...(sources.get(item.plugin_id)?.tags ?? []),
      ]),
    ],
    icon: item.icon ?? sources.get(item.plugin_id)?.icon,
  }));
  const rows =
    view === "Discover"
      ? [...sources.values()]
      : view === "Available to Install"
        ? available
        : view === "All"
          ? [...inventory, ...available]
          : view === "Updates Available"
            ? inventory.filter(
                (item) =>
                  item.available_update?.update_available || item.staged_update,
              )
            : inventory;
  return rows.filter(
    (item) =>
      `${item.name} ${item.plugin_id} ${item.description ?? ""}`
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (!tag || item.tags?.includes(tag)) &&
      (!channel || pluginChannel(item) === channel),
  );
}

export function pluginChannel(
  item: PluginSummary | PluginCatalogEntry,
): string {
  const channel =
    "status" in item
      ? item.trust?.signature_verified === true
        ? item.trust.publisher_channel
        : "unverified"
      : item.catalogue_channel;
  return channel === "official" || channel === "demo" ? channel : "community";
}

export function catalogueVersions(entry: PluginCatalogEntry) {
  const rows = new Map<
    string,
    { version: string; url: string; release_notes?: string | null }
  >([
    [
      entry.version,
      {
        version: entry.version,
        url: entry.url,
        release_notes: entry.release_notes,
      },
    ],
  ]);
  for (const release of entry.releases ?? []) {
    if (!rows.has(release.version)) rows.set(release.version, release);
  }
  return [...rows.values()];
}
