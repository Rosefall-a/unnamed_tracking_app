import type { PluginDiagnosticEvent, PluginSummary } from "./plugins";

function isolationFailure(message: string | null | undefined): boolean {
  return Boolean(message?.startsWith("Bubblewrap is unavailable"));
}

export function pluginIssues(plugin: PluginSummary): Array<[string, string]> {
  return [
    ["Compatibility", plugin.compatible ? null : plugin.compatibility_reason],
    ["Runtime", plugin.runtime_error],
    ["Plugin", plugin.last_error],
    ["Latest update", plugin.last_update_error],
  ].filter(
    (entry): entry is [string, string] =>
      typeof entry[1] === "string" &&
      entry[1].length > 0 &&
      !isolationFailure(entry[1]),
  );
}

export function recentPluginEvents(
  events: PluginDiagnosticEvent[],
): PluginDiagnosticEvent[] {
  return events
    .filter(
      (event) =>
        !(
          event.source === "runtime" &&
          event.event === "runtime.start_failed" &&
          event.message.startsWith(
            "Plugin startup failed: Bubblewrap is unavailable",
          )
        ),
    )
    .sort((a, b) => b.sequence - a.sequence);
}
