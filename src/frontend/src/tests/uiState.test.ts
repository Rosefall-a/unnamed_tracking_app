import { afterEach, describe, expect, it, vi } from "vitest";

function browserStore(items: Record<string, string>) {
  const map = new Map(Object.entries(items));
  return {
    map,
    store: {
      get length() {
        return map.size;
      },
      key: (i: number) => [...map.keys()][i] ?? null,
      getItem: (k: string) => map.get(k) ?? null,
      setItem: (k: string, v: string) => void map.set(k, v),
      removeItem: (k: string) => void map.delete(k),
      clear: () => map.clear(),
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("moving what an older version kept in the browser", () => {
  it("deletes a browser copy only once the server says it has it", async () => {
    const local = browserStore({
      manualCollections: '["Cozy"]',
      smartCollections: "[]",
      sidebarMode: "pinned",
    });
    vi.stubGlobal("localStorage", local.store);
    vi.stubGlobal("sessionStorage", browserStore({ x: "1" }).store);
    const sent: unknown[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url === "/api/ui-state/import") {
          sent.push(JSON.parse(String(init?.body)));
          // the server took one of the two real-data names
          return Response.json({
            stored: ["manualCollections"],
            rejected: [],
          });
        }
        return Response.json({ manualCollections: ["Cozy"] });
      }),
    );
    const { loadUiState, getUi } = await import("../state/uiState");
    await loadUiState("me");
    // a device choice is never sent
    expect(sent).toEqual([
      { values: { manualCollections: ["Cozy"], smartCollections: [] } },
    ]);
    expect([...local.map.keys()]).toEqual(["smartCollections", "sidebarMode"]);
    expect(getUi("manualCollections", [])).toEqual(["Cozy"]);
  });

  it("keeps every browser copy when the server cannot be reached", async () => {
    const local = browserStore({ manualCollections: '["Cozy"]' });
    vi.stubGlobal("localStorage", local.store);
    vi.stubGlobal("sessionStorage", browserStore({}).store);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("offline");
      }),
    );
    const { loadUiState } = await import("../state/uiState");
    await loadUiState("me");
    expect(local.map.get("manualCollections")).toBe('["Cozy"]');
  });

  it("writes device choices back to the browser, then removes them from the server", async () => {
    const local = browserStore({ statsTab: "games" });
    vi.stubGlobal("localStorage", local.store);
    vi.stubGlobal("sessionStorage", browserStore({}).store);
    const deleted: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === "DELETE") {
          deleted.push(url);
          return new Response(null, { status: 204 });
        }
        return Response.json({
          sidebarMode: "rail",
          sidebarWidth: 260,
          "bluemap-lang": "en",
          statsTab: "overview",
          "homePick:w1": { day: "2026-11-10", key: "anime:1" },
        });
      }),
    );
    const { loadUiState, getUi } = await import("../state/uiState");
    await loadUiState("me");
    expect(local.map.get("sidebarMode")).toBe("rail");
    expect(local.map.get("sidebarWidth")).toBe("260");
    expect(local.map.get("bluemap-lang")).toBe('"en"');
    // what this browser already had wins
    expect(local.map.get("statsTab")).toBe("games");
    expect(deleted.sort()).toEqual([
      "/api/ui-state/bluemap-lang",
      "/api/ui-state/sidebarMode",
      "/api/ui-state/sidebarWidth",
      "/api/ui-state/statsTab",
    ]);
    expect(getUi("homePick:w1", null)).toEqual({
      day: "2026-11-10",
      key: "anime:1",
    });
    expect(getUi("sidebarMode", "overlay")).toBe("rail");
  });
});
