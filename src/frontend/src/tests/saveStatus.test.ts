import { afterEach, describe, expect, it, vi } from "vitest";
import {
  savedAt,
  saveState,
  startTrackingSaves,
  stopTrackingSaves,
} from "../state/saveStatus";

afterEach(() => {
  stopTrackingSaves();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function track(fetch = vi.fn().mockResolvedValue(new Response())) {
  const browser = { fetch };
  vi.stubGlobal("window", browser);
  startTrackingSaves();
  return browser;
}

describe("settings save feedback", () => {
  it("leaves plugin configuration loads and command failures to their active UI", async () => {
    const browser = track(
      vi.fn().mockResolvedValue(new Response("unavailable", { status: 503 })),
    );
    await browser.fetch("/api/plugins/example/actions/get-config", {
      method: "POST",
    });
    expect(saveState.value).toBe("idle");
    expect(savedAt.value).toBeNull();
    await browser.fetch("/api/plugins/example/settings", { method: "PUT" });
    expect(saveState.value).toBe("error");
  });

  it("confirms for twelve seconds, then becomes quiet Saved feedback", async () => {
    vi.useFakeTimers();
    const browser = track();
    await browser.fetch("/api/preferences", { method: "PUT" });
    expect(saveState.value).toBe("saved");
    expect(savedAt.value).toBeTypeOf("number");
    await vi.advanceTimersByTimeAsync(11_999);
    expect(saveState.value).toBe("saved");
    await vi.advanceTimersByTimeAsync(1);
    expect(saveState.value).toBe("settled");
    await browser.fetch("/api/preferences", { method: "PUT" });
    expect(saveState.value).toBe("saved");
  });

  it("keeps a failed concurrent write visible after another succeeds", async () => {
    let complete!: (response: Response) => void;
    const fetch = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            complete = resolve;
          }),
      )
      .mockResolvedValueOnce(new Response("invalid", { status: 400 }));
    const browser = track(fetch);
    const first = browser.fetch("/api/settings/a", { method: "PUT" });
    await browser.fetch("/api/settings/b", { method: "PUT" });
    complete(new Response());
    await first;
    expect(saveState.value).toBe("error");
    fetch.mockResolvedValue(new Response());
    await browser.fetch("/api/settings/b", { method: "PUT" });
    expect(saveState.value).toBe("saved");
  });

  it("ignores late responses from a closed settings session and clears its timer", async () => {
    vi.useFakeTimers();
    let complete!: (response: Response) => void;
    const fetch = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            complete = resolve;
          }),
      )
      .mockResolvedValue(new Response());
    const browser = track(fetch);
    const oldFetch = browser.fetch;
    const oldWrite = browser.fetch("/api/preferences", { method: "PATCH" });
    stopTrackingSaves();
    expect(browser.fetch).toBe(fetch);
    startTrackingSaves();
    complete(new Response());
    await oldWrite;
    expect(saveState.value).toBe("idle");
    await oldFetch("/api/preferences", { method: "PATCH" });
    expect(saveState.value).toBe("idle");
    await browser.fetch("/api/preferences", { method: "PATCH" });
    stopTrackingSaves();
    await vi.advanceTimersByTimeAsync(12_000);
    expect(saveState.value).toBe("idle");
    expect(savedAt.value).toBeNull();
  });

  it("reports network failure and ignores reads or non-API requests", async () => {
    const fetch = vi
      .fn()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue(new Response());
    const browser = track(fetch);
    await expect(
      browser.fetch("/api/preferences", { method: "PUT" }),
    ).rejects.toThrow("offline");
    expect(saveState.value).toBe("error");
    await browser.fetch("/api/settings");
    await browser.fetch("https://example.invalid/submit", { method: "POST" });
    expect(saveState.value).toBe("error");
  });
});
