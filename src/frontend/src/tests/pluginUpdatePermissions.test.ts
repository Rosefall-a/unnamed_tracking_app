import { afterEach, expect, it, vi } from "vitest";
import { updatePlugin, updatePluginFromUrl } from "../services/plugins";

afterEach(() => vi.unstubAllGlobals());

it("binds selected upload permissions to a completed payload review", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify({ status: "running" })));
  vi.stubGlobal("fetch", fetch);
  const digest = "a".repeat(64);
  await updatePlugin(
    "example.update",
    new File(["package"], "candidate.utp"),
    { approvedPermissions: ["media.read:v1"], expectedDigest: digest },
    true,
  );
  const [url, options] = fetch.mock.calls[0];
  const query = new URL(url, "https://host.example").searchParams;
  expect(query.get("permissions_reviewed")).toBe("true");
  expect(query.getAll("approved_permissions")).toEqual(["media.read:v1"]);
  expect(options.body.get("expected_digest")).toBe(digest);
});

it("marks URL review complete while retaining its selected access and digest", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify({ status: "running" })));
  vi.stubGlobal("fetch", fetch);
  const digest = "b".repeat(64);
  await updatePluginFromUrl(
    "example.update",
    "https://packages.example/candidate.utp",
    { approvedPermissions: ["media.read:v1"] },
    digest,
    true,
  );
  const [url, options] = fetch.mock.calls[0];
  const query = new URL(url, "https://host.example").searchParams;
  expect(query.get("permissions_reviewed")).toBe("true");
  expect(query.getAll("approved_permissions")).toEqual(["media.read:v1"]);
  expect(JSON.parse(options.body).expected_digest).toBe(digest);
});
