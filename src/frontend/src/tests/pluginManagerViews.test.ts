import { describe, expect, it } from "vitest";
import {
  managerEntries,
  pluginChannel,
  catalogueVersions,
} from "../services/pluginManagerViews";
import type { PluginCatalogEntry, PluginSummary } from "../services/plugins";
const installed: PluginSummary = {
  plugin_id: "media.sync",
  name: "Media Sync",
  version: "1.0.0",
  description: "Sync library",
  tags: ["media"],
  status: "disabled",
  enabled: false,
  compatible: true,
  compatibility_reason: "",
  permissions: [],
  granted_capabilities: [],
  effective_capabilities: [],
  health: "unknown",
  available_update: {
    plugin_id: "media.sync",
    current_version: "1.0.0",
    available_version: "2.0.0",
    update_available: true,
  },
};
const catalogue: PluginCatalogEntry[] = [
  {
    plugin_id: "media.sync",
    name: "Media Sync",
    description: "Sync",
    version: "2.0.0",
    url: "https://first.example/sync.utp",
  },
  {
    plugin_id: "media.sync",
    name: "Media Sync",
    description: "Sync",
    version: "2.0.0",
    url: "https://second.example/sync.utp",
  },
  {
    plugin_id: "sessions.self",
    name: "Session Manager",
    description: "Manage sessions",
    version: "1.0.0",
    url: "https://first.example/session.utp",
    tags: ["account"],
  },
];
describe("authoritative Plugin Manager views", () => {
  it("shows installed plugins independently of live contributions", () =>
    expect(managerEntries([installed], catalogue, "Installed")).toEqual([
      installed,
    ]));
  it("deduplicates catalogue identities and includes installed-only plugins", () => {
    const local = { ...installed, plugin_id: "local.plugin" };
    expect(
      managerEntries([installed, local], catalogue, "All").map(
        (item) => item.plugin_id,
      ),
    ).toEqual(["media.sync", "local.plugin", "sessions.self"]);
  });
  it("offers updates and excludes existing installations from install view", () => {
    expect(managerEntries([installed], catalogue, "Updates Available")).toEqual(
      [installed],
    );
    expect(
      managerEntries([installed], catalogue, "Available to Install").map(
        (item) => item.plugin_id,
      ),
    ).toEqual(["sessions.self"]);
  });
  it("filters using publisher-provided tags and searchable text", () => {
    expect(
      managerEntries([installed], catalogue, "All", "library", "media"),
    ).toEqual([installed]);
    expect(
      managerEntries([installed], catalogue, "All", "session", "account"),
    ).toHaveLength(1);
    expect(
      managerEntries([installed], catalogue, "All", "session", "media"),
    ).toHaveLength(0);
  });
});

describe("discovery and release selection", () => {
  it("offers one deduplicated discovery catalogue including installed releases", () => {
    expect(
      managerEntries([installed], catalogue, "Discover").map(
        (entry) => entry.plugin_id,
      ),
    ).toEqual(["media.sync", "sessions.self"]);
  });
  it("filters registry categories without treating names or tags as verified publishers", () => {
    const entries = [
      { ...catalogue[0]!, catalogue_channel: "official" as const },
      { ...catalogue[2]!, catalogue_channel: "demo" as const },
    ];
    expect(managerEntries([], entries, "Discover", "", "", "demo")).toEqual([
      entries[1],
    ]);
    expect(
      pluginChannel({
        ...installed,
        name: "Official",
        trust: { publisher_channel: "official", signature_verified: false },
      }),
    ).toBe("community");
    expect(
      pluginChannel({
        ...installed,
        trust: { publisher_channel: "official", signature_verified: true },
      }),
    ).toBe("official");
  });
  it("keeps the current release first and deduplicates retained releases", () => {
    const entry = {
      ...catalogue[0]!,
      releases: [
        { version: "2.0.0", url: "duplicate" },
        { version: "1.0.0", url: "old" },
      ],
    };
    expect(
      catalogueVersions(entry).map((release) => [release.version, release.url]),
    ).toEqual([
      ["2.0.0", entry.url],
      ["1.0.0", "old"],
    ]);
  });
});
