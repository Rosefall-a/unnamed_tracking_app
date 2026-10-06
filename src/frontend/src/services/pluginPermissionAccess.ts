import type { PluginInstallPermission } from "./plugins";
import type {
  PluginPermissionGrant,
  PluginPermissionRequest,
} from "./pluginPermissions";

export interface PermissionAccessRow {
  key: string;
  permission: PluginInstallPermission;
  grant?: PluginPermissionGrant;
  request?: PluginPermissionRequest;
  userId: string | null;
  deviceId: string | null;
  coveredBy?: string;
  state: "active" | "pending" | "denied";
}

const riskOrder = { critical: 0, high: 1, medium: 2, low: 3 };
const scopeKey = (key: string, user: string | null, device: string | null) =>
  JSON.stringify([key, user, device]);

export function permissionAccessRows(
  permissions: PluginInstallPermission[],
  grants: PluginPermissionGrant[],
  requests: PluginPermissionRequest[],
): PermissionAccessRow[] {
  const declarations = new Map(permissions.map((item) => [item.key, item]));
  const rows = new Map<string, PermissionAccessRow>();
  const getRow = (
    permission: PluginInstallPermission,
    userId: string | null,
    deviceId: string | null,
  ) => {
    const key = scopeKey(permission.key, userId, deviceId);
    let row = rows.get(key);
    if (!row) {
      row = { key, permission, userId, deviceId, state: "denied" };
      rows.set(key, row);
    }
    return row;
  };
  permissions.forEach((permission) => getRow(permission, null, null));
  for (const grant of grants) {
    const declaration = declarations.get(
      `${grant.capability}:v${grant.capability_version}`,
    );
    if (!declaration) continue;
    const row = getRow(declaration, grant.user_id, grant.device_id);
    const current = row.grant;
    if (
      !current ||
      (grant.active && !current.active) ||
      (grant.active === current.active && grant.id < current.id)
    )
      row.grant = grant;
  }
  for (const request of requests) {
    const declaration = declarations.get(
      `${request.capability}:v${request.capability_version}`,
    );
    if (!declaration || request.status !== "pending") continue;
    const row = getRow(declaration, request.user_id, null);
    if (!row.request || request.id < row.request.id) row.request = request;
  }
  for (const row of rows.values()) {
    row.state = row.grant?.active
      ? "active"
      : row.request
        ? "pending"
        : "denied";
    if (row.grant || row.request) continue;
    let parent = row.permission.parent;
    const visited = new Set<string>();
    while (parent && !visited.has(parent)) {
      visited.add(parent);
      const key = `${parent}:v${row.permission.capability_version}`;
      const ancestor = rows.get(scopeKey(key, row.userId, row.deviceId));
      if (ancestor?.grant?.active) {
        row.state = "active";
        row.coveredBy = ancestor.permission.title;
        break;
      }
      parent = declarations.get(key)?.parent ?? null;
    }
  }
  return [...rows.values()].sort(
    (a, b) =>
      a.permission.category.localeCompare(b.permission.category) ||
      riskOrder[a.permission.risk] - riskOrder[b.permission.risk] ||
      a.permission.title.localeCompare(b.permission.title) ||
      a.key.localeCompare(b.key),
  );
}

export function permissionIcon(capability: string): string {
  const icons: Record<string, string> = {
    users: "account",
    sessions: "account",
    games: "games",
    media: "media",
    documents: "folder",
    notifications: "notifications",
    tasks: "calendar",
    storage: "folder",
  };
  return icons[capability.split(".")[0] ?? ""] ?? "plugin";
}
