import { describe, expect, it } from "vitest";
import { permissionAccessRows } from "../services/pluginPermissionAccess";
import type { PluginInstallPermission } from "../services/plugins";
import type { PluginPermissionGrant } from "../services/pluginPermissions";

function permission(
  capability: string,
  title: string,
  risk: PluginInstallPermission["risk"] = "low",
  parent: string | null = null,
): PluginInstallPermission {
  return {
    key: `${capability}:v1`,
    capability,
    capability_version: 1,
    title,
    risk,
    category: "Library",
    parent,
    children: [],
    rationale: "Reviewed access",
    highly_privileged: risk === "critical",
  };
}
const read = permission("games.read", "Read games");
const write = permission("games.write", "Edit games", "high");
function grant(
  capability: string,
  changes: Partial<PluginPermissionGrant> = {},
): PluginPermissionGrant {
  return {
    id: capability,
    plugin_id: "test.plugin",
    installation_id: "installation",
    capability,
    capability_version: 1,
    user_id: null,
    device_id: null,
    active: true,
    granted_at: 1,
    revoked_at: null,
    ...changes,
  };
}

describe("native permission access groups", () => {
  it("shows one logical permission across older revoked and active records", () => {
    const rows = permissionAccessRows(
      [read],
      [
        grant("games.read", { id: "old", active: false, revoked_at: 2 }),
        grant("games.read", { id: "new" }),
      ],
      [],
    );
    expect(rows).toHaveLength(1);
    expect(rows[0]?.grant?.id).toBe("new");
    expect(rows[0]?.state).toBe("active");
  });
  it("keeps a stable risk/name order independently of approval time or input order", () => {
    const a = grant("games.read", { granted_at: 100 });
    const b = grant("games.write", { granted_at: 1 });
    const view = (grants: PluginPermissionGrant[]) =>
      permissionAccessRows([read, write], grants, []).map(
        (row) => row.permission.key,
      );
    expect(view([a, b])).toEqual([write.key, read.key]);
    expect(view([b, { ...a, granted_at: 200 }])).toEqual([write.key, read.key]);
    expect(view([{ ...a, active: false, revoked_at: 3 }, b])).toEqual([
      write.key,
      read.key,
    ]);
  });
  it("retains distinct user/device scopes instead of broadening a personal grant", () => {
    const rows = permissionAccessRows(
      [read],
      [
        grant("games.read", { id: "personal", user_id: "user" }),
        grant("games.read", {
          id: "device",
          user_id: "user",
          device_id: "device",
        }),
      ],
      [],
    );
    expect(rows).toHaveLength(3);
    expect(rows.find((row) => !row.userId)?.state).toBe("denied");
    expect(rows.filter((row) => row.state === "active")).toHaveLength(2);
  });
  it("shows inherited access while an explicit revocation overrides its parent", () => {
    const parent = permission("games", "Game API", "critical");
    const leaf = { ...read, parent: "games" };
    const allowed = permissionAccessRows([parent, leaf], [grant("games")], []);
    expect(
      allowed.find((row) => row.permission.key === read.key)?.coveredBy,
    ).toBe("Game API");
    const denied = permissionAccessRows(
      [parent, leaf],
      [grant("games"), grant("games.read", { active: false, revoked_at: 1 })],
      [],
    );
    expect(denied.find((row) => row.permission.key === read.key)?.state).toBe(
      "denied",
    );
  });
});
