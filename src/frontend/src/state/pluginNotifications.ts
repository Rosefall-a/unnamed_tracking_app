import { ref } from "vue";
import { pluginRecordPathAllowed } from "./pluginSearch";

export interface PluginReminder {
  id: string;
  label: string;
  description: string;
  path: string;
}
type Provider = () => Promise<PluginReminder[]>;
const providers = new Map<string, Provider>();
export const pluginReminderRevision = ref(0);

export function registerPluginReminders(
  pluginId: string,
  provider: Provider,
): () => void {
  providers.set(pluginId, provider);
  pluginReminderRevision.value++;
  return () => {
    if (providers.get(pluginId) === provider) {
      providers.delete(pluginId);
      pluginReminderRevision.value++;
    }
  };
}

export async function readPluginReminders(): Promise<
  Array<PluginReminder & { pluginId: string }>
> {
  const results = await Promise.all(
    [...providers].map(async ([pluginId, provider]) => {
      try {
        const items = await provider();
        if (providers.get(pluginId) !== provider) return [];
        return items
          .filter(
            (item) =>
              typeof item?.id === "string" &&
              typeof item.label === "string" &&
              typeof item.description === "string" &&
              pluginRecordPathAllowed(pluginId, item.path),
          )
          .slice(0, 50)
          .map((item) => ({ ...item, pluginId }));
      } catch {
        return [];
      }
    }),
  );
  return results.flat().slice(0, 200);
}
