import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  vi.resetModules();
});

function stubNotifications(unread: number) {
  const fetchMock = vi.fn().mockImplementation(
    async () =>
      new Response(JSON.stringify({ items: [], unread }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("notification refresh", () => {
  it("shares one request between bells mounting together", async () => {
    const fetchMock = stubNotifications(3);
    const state = await import("../state/notifications");
    await Promise.all([
      state.refreshMediaNotifications({ maxAgeMs: 30_000 }),
      state.refreshMediaNotifications({ maxAgeMs: 30_000 }),
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(state.mediaUnread.value).toBe(3);
  });

  it("keeps a recent list for a page change, but not past its age", async () => {
    vi.useFakeTimers();
    const fetchMock = stubNotifications(1);
    const state = await import("../state/notifications");
    await state.refreshMediaNotifications({ maxAgeMs: 30_000 });
    await state.refreshMediaNotifications({ maxAgeMs: 30_000 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(31_000);
    await state.refreshMediaNotifications({ maxAgeMs: 30_000 });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("always asks again when no age is given (after marking or deleting)", async () => {
    const fetchMock = stubNotifications(0);
    const state = await import("../state/notifications");
    await state.refreshMediaNotifications({ maxAgeMs: 30_000 });
    await state.refreshMediaNotifications();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
