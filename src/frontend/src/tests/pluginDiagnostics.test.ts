import { describe, expect, it } from "vitest";
import {
  pluginIssues,
  recentPluginEvents,
} from "../services/pluginDiagnostics";
import type { PluginDiagnosticEvent, PluginSummary } from "../services/plugins";

const plugin: PluginSummary = {
  plugin_id: "test.plugin",
  name: "Test",
  version: "1.1.0",
  status: "running",
  compatible: true,
  compatibility_reason: "",
  health: "healthy",
  enabled: true,
  permissions: [],
  granted_capabilities: [],
  effective_capabilities: [],
  runtime: {
    bubblewrap_available: false,
    sandbox_available: false,
    mechanism: "process",
    reduced_isolation_allowed: true,
    last_error: "bwrap: namespace creation denied",
  },
};
function event(
  sequence: number,
  changes: Partial<PluginDiagnosticEvent> = {},
): PluginDiagnosticEvent {
  return {
    sequence,
    timestamp: "2026-10-05T12:00:00Z",
    level: "info",
    event: "action.completed",
    message: "Complete",
    source: "runtime",
    plugin_id: "test.plugin",
    correlation_id: null,
    metadata: {},
    ...changes,
  };
}
describe("plugin diagnostics and server isolation", () => {
  it("keeps the server isolation probe out of otherwise healthy plugin issues", () => {
    expect(pluginIssues(plugin)).toEqual([]);
    expect(
      pluginIssues({
        ...plugin,
        last_error: "Bubblewrap is unavailable. Approval required.",
      }),
    ).toEqual([]);
  });
  it("retains plugin and update errors with their source labels", () => {
    expect(
      pluginIssues({
        ...plugin,
        last_error: "Worker exited with code 1",
        last_update_error: "Package digest differs",
      }),
    ).toEqual([
      ["Plugin", "Worker exited with code 1"],
      ["Latest update", "Package digest differs"],
    ]);
  });
  it("puts the newest sequence first without changing the source buffer", () => {
    const buffer = [event(1), event(3), event(2)];
    expect(recentPluginEvents(buffer).map((item) => item.sequence)).toEqual([
      3, 2, 1,
    ]);
    expect(buffer.map((item) => item.sequence)).toEqual([1, 3, 2]);
  });
  it("hides historical server policy failures while retaining real plugin stderr", () => {
    const message =
      "Plugin startup failed: Bubblewrap is unavailable. Approval required.";
    const buffer = [
      event(1, { event: "runtime.start_failed", level: "error", message }),
      event(2, {
        event: "plugin.stderr",
        source: "plugin",
        level: "error",
        message,
      }),
    ];
    expect(recentPluginEvents(buffer).map((item) => item.sequence)).toEqual([
      2,
    ]);
  });
});
