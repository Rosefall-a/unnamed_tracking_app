import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const publicFile = (name: string) =>
  readFileSync(new URL(`../../public/${name}`, import.meta.url), "utf8");

describe("PWA metadata", () => {
  it("provides installable standalone metadata and two PNG icon sizes", () => {
    const manifest = JSON.parse(publicFile("manifest.webmanifest"));
    expect(manifest.display).toBe("standalone");
    expect(manifest.start_url).toBe("/");
    expect(manifest.icons.map((icon: { sizes: string }) => icon.sizes)).toEqual([
      "192x192",
      "512x512",
    ]);
  });

  it("never caches API responses and has a safe offline page", () => {
    const worker = publicFile("service-worker.js");
    expect(worker).toContain('url.pathname.startsWith("/api/")');
    expect(worker).toContain('request.method !== "GET"');
    expect(worker).toContain("/offline.html");
  });
});
