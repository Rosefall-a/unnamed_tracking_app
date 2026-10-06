import { afterEach, describe, expect, it, vi } from "vitest";
import {
  DEFAULT_PREFERENCES,
  invalidateQueuedPreferences,
  queuePreferences,
} from "../services/preferences";

afterEach(() => {
  invalidateQueuedPreferences();
  vi.unstubAllGlobals();
});

describe("preference saves across sessions", () => {
  it("does not send an old account's queued change with a new session", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    const save = queuePreferences({ ui_theme: "dark" });
    invalidateQueuedPreferences();
    await expect(save).rejects.toThrow("session changed");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("rejects late responses while allowing the new account to save", async () => {
    let complete!: (response: Response) => void;
    const fetch = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            complete = resolve;
          }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ ...DEFAULT_PREFERENCES, ui_theme: "light" }),
        ),
      );
    vi.stubGlobal("fetch", fetch);
    const oldSave = queuePreferences({ ui_theme: "dark" });
    await Promise.resolve();
    invalidateQueuedPreferences();
    const newSave = queuePreferences({ ui_theme: "light" });
    complete(
      new Response(
        JSON.stringify({ ...DEFAULT_PREFERENCES, ui_theme: "dark" }),
      ),
    );
    await expect(oldSave).rejects.toThrow("session changed");
    expect(await newSave).toMatchObject({
      latest: true,
      prefs: { ui_theme: "light" },
    });
  });
});
