import { describe, expect, it } from "vitest";
import {
  navigationFolderNodes,
  pluginPlacementGroup,
} from "../utils/pluginPlacement";

describe("extension placement", () => {
  it("joins a core header only with the separate area permission", () => {
    expect(pluginPlacementGroup("library", ["Library"], false)).toBe(
      "Extensions",
    );
    expect(pluginPlacementGroup("library", ["Library"], true)).toBe("Library");
    expect(pluginPlacementGroup("My tools", ["Library"], false)).toBe(
      "My tools",
    );
  });
  it("groups nested entries without losing their targets or order", () => {
    const entries = [
      { id: "first", label: "First", folders: [], path: "/first" },
      { id: "a", label: "A", folders: ["Tools", "Advanced"], path: "/a" },
      { id: "b", label: "B", folders: ["Tools"], path: "/b" },
      { id: "last", label: "Last", folders: [], path: "/last" },
    ];
    const nodes = navigationFolderNodes(entries);
    expect(nodes.map((node) => node.id)).toEqual([
      "entry:first",
      "folder:Tools",
      "entry:last",
    ]);
    const folder = nodes[1];
    if (folder?.kind !== "folder") throw new Error("Missing folder");
    expect(
      folder.entries.map((item) => [item.id, item.path, item.folders]),
    ).toEqual([
      ["a", "/a", ["Advanced"]],
      ["b", "/b", []],
    ]);
    expect(entries[1]?.folders).toEqual(["Tools", "Advanced"]);
  });
});
