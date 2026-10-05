import { expect, it } from "vitest";
import {
  registerPluginSearch,
  searchPluginRecords,
} from "../state/pluginSearch";

it("accepts owned plugin routes and removes withdrawn search providers", async () => {
  const stop = registerPluginSearch("example.archive", async (query) => [
    {
      id: "owned",
      label: query,
      path: "/plugins/example.archive/cards?record_id=1",
    },
    { id: "external", label: "External", path: "https://evil.invalid/" },
    {
      id: "escape",
      label: "Escape",
      path: "/plugins/example.archive/../../../settings",
    },
    { id: "other", label: "Other", path: "/plugins/example.other/home" },
  ]);
  try {
    expect((await searchPluginRecords("Quest")).map((item) => item.id)).toEqual(
      ["owned"],
    );
  } finally {
    stop();
  }
  expect(await searchPluginRecords("Quest")).toEqual([]);
});
it("discards in-flight results after removal and isolates a failing provider", async () => {
  let finish!: (
    items: Array<{ id: string; label: string; path: string }>,
  ) => void;
  const stop = registerPluginSearch(
    "example.pending",
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const fail = registerPluginSearch("example.broken", async () => {
    throw new Error("Denied");
  });
  const pending = searchPluginRecords("Quest");
  stop();
  finish([
    { id: "owned", label: "Quest", path: "/plugins/example.pending/cards" },
  ]);
  try {
    expect(await pending).toEqual([]);
  } finally {
    fail();
  }
});
