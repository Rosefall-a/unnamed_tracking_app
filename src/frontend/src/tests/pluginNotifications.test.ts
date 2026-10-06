import { expect, it } from "vitest";
import {
  registerPluginReminders,
  readPluginReminders,
} from "../state/pluginNotifications";

it("shows plugin-owned reminders and drops revoked results while isolating failures", async () => {
  let finish!: (
    items: Array<{
      id: string;
      label: string;
      description: string;
      path: string;
    }>,
  ) => void;
  const remove = registerPluginReminders(
    "example.archive",
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const bad = registerPluginReminders("example.failure", async () => {
    throw new Error("Offline");
  });
  const pending = readPluginReminders();
  remove();
  finish([
    {
      id: "due",
      label: "Quest",
      description: "Due today",
      path: "/plugins/example.archive/bounties",
    },
  ]);
  expect(await pending).toEqual([]);
  bad();
  const stop = registerPluginReminders("example.archive", async () => [
    {
      id: "due",
      label: "Quest",
      description: "Due today",
      path: "/plugins/example.archive/bounties?record_id=1",
    },
    {
      id: "escape",
      label: "Bad",
      description: "Bad",
      path: "/plugins/example.archive/../../settings",
    },
  ]);
  try {
    expect((await readPluginReminders()).map((item) => item.id)).toEqual([
      "due",
    ]);
  } finally {
    stop();
  }
});
