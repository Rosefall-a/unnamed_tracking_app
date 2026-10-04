import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

it.each([false, true])(
  "delayed update reload respects current online state (%s)",
  async (online) => {
    await import("vue");
    const workers = new EventTarget();
    const reload = vi.fn();
    const navigator = {
      onLine: true,
      serviceWorker: Object.assign(workers, {
        controller: { scriptURL: "https://archive.test/service-worker.js" },
        getRegistrations: async () => [],
      }),
    };
    vi.stubGlobal("navigator", navigator);
    vi.stubGlobal(
      "window",
      Object.assign(new EventTarget(), {
        setInterval: vi.fn(),
        location: { reload },
      }),
    );
    vi.stubGlobal(
      "document",
      Object.assign(new EventTarget(), {
        readyState: "complete",
        querySelector: () => null,
      }),
    );
    let finish!: (response: Response) => void;
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(new Response('{"enabled":false}'))
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            finish = resolve;
          }),
      );
    vi.stubGlobal("fetch", fetch);
    const { startPwa, pwaState } = await import("../services/pwa");
    startPwa();
    await vi.waitFor(() => expect(pwaState.available).toBe(true));
    workers.dispatchEvent(new Event("controllerchange"));
    expect(fetch).toHaveBeenCalledTimes(2);
    navigator.onLine = online;
    if (!online) window.dispatchEvent(new Event("offline"));
    finish(new Response('{"enabled":true}'));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(reload).toHaveBeenCalledTimes(online ? 1 : 0);
    expect(pwaState.online).toBe(online);
  },
);
