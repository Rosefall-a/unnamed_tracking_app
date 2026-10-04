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

it.each([true, false])(
  "queues an early install prompt only for a verified enabled provider (%s)",
  async (enabled) => {
    await import("vue");
    const window = Object.assign(new EventTarget(), {
      setInterval: vi.fn(),
      isSecureContext: true,
      location: { reload: vi.fn() },
    });
    const workers = Object.assign(new EventTarget(), {
      controller: null,
      getRegistrations: async () => [],
      getRegistration: async () => undefined,
      register: async () => ({}),
    });
    vi.stubGlobal("window", window);
    vi.stubGlobal("navigator", { onLine: true, serviceWorker: workers });
    vi.stubGlobal(
      "document",
      Object.assign(new EventTarget(), {
        readyState: "complete",
        querySelector: () => null,
        createElement: () => ({ dataset: {} }),
        head: { append: vi.fn() },
      }),
    );
    let finish!: (response: Response) => void;
    vi.stubGlobal(
      "fetch",
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const { startPwa, pwaState, installPwa } = await import("../services/pwa");
    startPwa();
    const prompt = vi.fn(async () => {});
    const event = Object.assign(
      new Event("beforeinstallprompt", { cancelable: true }),
      {
        prompt,
        userChoice: Promise.resolve({ outcome: "accepted" }),
      },
    );
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    expect(pwaState.installable).toBe(false);
    await installPwa();
    expect(prompt).not.toHaveBeenCalled();
    finish(new Response(JSON.stringify({ enabled, generation: "provider" })));
    await vi.waitFor(() => expect(pwaState.available).toBe(true));
    await vi.waitFor(() => expect(pwaState.installable).toBe(enabled));
    await installPwa();
    expect(prompt).toHaveBeenCalledTimes(enabled ? 1 : 0);
    expect(pwaState.installable).toBe(false);
  },
);
