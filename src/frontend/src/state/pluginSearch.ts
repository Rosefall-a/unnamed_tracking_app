/** Native plugins own search data; the host owns lifecycle and destinations. */
export interface PluginSearchResult {
  id: string;
  label: string;
  description?: string;
  path: string;
}
type SearchProvider = (query: string) => Promise<PluginSearchResult[]>;
const providers = new Map<string, SearchProvider>();

export function pluginRecordPathAllowed(
  pluginId: string,
  path: unknown,
): boolean {
  if (typeof path !== "string") return false;
  const prefix = `/plugins/${encodeURIComponent(pluginId)}/`;
  return (
    path.startsWith(prefix) &&
    new URL(path, "https://host.invalid").pathname.startsWith(prefix)
  );
}

export function registerPluginSearch(
  pluginId: string,
  provider: SearchProvider,
): () => void {
  providers.set(pluginId, provider);
  return () => {
    if (providers.get(pluginId) === provider) providers.delete(pluginId);
  };
}

export async function searchPluginRecords(
  query: string,
): Promise<Array<PluginSearchResult & { pluginId: string }>> {
  if (!query.trim()) return [];
  const results = await Promise.all(
    [...providers].map(async ([pluginId, provider]) => {
      try {
        const matches = await provider(query);
        if (providers.get(pluginId) !== provider) return [];
        return matches
          .filter(
            (item) =>
              typeof item?.id === "string" &&
              typeof item.label === "string" &&
              pluginRecordPathAllowed(pluginId, item.path),
          )
          .slice(0, 6)
          .map((item) => ({ ...item, pluginId }));
      } catch {
        return [];
      }
    }),
  );
  return results.flat().slice(0, 12);
}
