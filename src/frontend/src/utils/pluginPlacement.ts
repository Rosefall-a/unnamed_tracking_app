export type SettingsArea = "account" | "preferences" | "administration";

export const SIDEBAR_BUILT_IN_GROUPS = ["Your library", "Keep track"];
export const SETTINGS_BUILT_IN_GROUPS: Record<SettingsArea, string[]> = {
  account: ["Account"],
  preferences: ["Preferences", "Library", "Information"],
  administration: ["Server management"],
};
export const SETTINGS_PLACEMENT_CAPABILITIES: Record<SettingsArea, string> = {
  account: "frontend.placement.settings.account",
  preferences: "frontend.placement.settings.preferences",
  administration: "frontend.placement.settings.admin",
};

export function pluginPlacementGroup(
  requested: string | undefined,
  builtInGroups: string[],
  allowed: boolean,
): string {
  const group = requested?.trim() || "Extensions";
  const builtIn = builtInGroups.find(
    (label) => label.toLowerCase() === group.toLowerCase(),
  );
  return builtIn ? (allowed ? builtIn : "Extensions") : group;
}

export interface NavigationFolderEntry {
  id: string;
  label: string;
  folders?: readonly string[];
}

export type NavigationFolderNode<T extends NavigationFolderEntry> =
  | { kind: "entry"; id: string; entry: T }
  | { kind: "folder"; id: string; label: string; entries: T[] };

export function navigationFolderNodes<T extends NavigationFolderEntry>(
  entries: readonly T[],
): NavigationFolderNode<T>[] {
  const nodes: NavigationFolderNode<T>[] = [];
  const folders = new Map<string, T[]>();
  for (const entry of entries) {
    const folder = entry.folders?.[0];
    if (!folder) {
      nodes.push({ kind: "entry", id: `entry:${entry.id}`, entry });
      continue;
    }
    let contents = folders.get(folder);
    if (!contents) {
      contents = [];
      folders.set(folder, contents);
      nodes.push({
        kind: "folder",
        id: `folder:${folder}`,
        label: folder,
        entries: contents,
      });
    }
    contents.push({ ...entry, folders: entry.folders?.slice(1) });
  }
  return nodes;
}
