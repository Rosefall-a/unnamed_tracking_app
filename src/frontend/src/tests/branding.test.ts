import { afterEach, expect, it, vi } from "vitest";
import { applyBranding, branding, loadBranding } from "../state/branding";

afterEach(() => {
  vi.unstubAllGlobals();
});

it("does not replace a successful branding save with an older initial read", async () => {
  const previous = branding.value;
  const favicon = { href: "", type: "" };
  vi.stubGlobal("document", { querySelector: () => favicon });
  let complete!: (response: Response) => void;
  vi.stubGlobal(
    "fetch",
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          complete = resolve;
        }),
    ),
  );
  try {
    const loading = loadBranding();
    const saved = {
      app_name: "Saved name",
      logo_url: null,
      favicon_url: "/api/branding/assets/favicon/new.png",
    };
    applyBranding(saved);
    complete(new Response(JSON.stringify(previous)));
    await loading;
    expect(branding.value).toEqual(saved);
    expect(favicon).toEqual({ href: saved.favicon_url, type: "image/png" });
  } finally {
    applyBranding(previous);
  }
});
