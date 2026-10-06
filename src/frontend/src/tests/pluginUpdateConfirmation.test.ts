import { afterEach, expect, it, vi } from "vitest";
import { updatePlugin, updatePluginFromUrl } from "../services/plugins";

afterEach(() => vi.unstubAllGlobals());
const digest = "a".repeat(64);
const confirmation = {
  approvedPermissions: ["games.read:v1"],
  versionChangeConfirmed: true,
  expectedInstalledVersion: "1.2.0",
  expectedDigest: digest,
};

it("sends upload confirmation with the reviewed package and installed-version snapshots", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify({ status: "active" })));
  vi.stubGlobal("fetch", fetch);
  await updatePlugin(
    "example.update",
    new File(["package"], "preview.upt"),
    confirmation,
    true,
  );
  const [url, request] = fetch.mock.calls[0];
  const query = new URL(url, "https://host.example").searchParams;
  expect(query.get("version_change_confirmed")).toBe("true");
  expect(query.getAll("approved_permissions")).toEqual(["games.read:v1"]);
  expect(request.body.get("expected_digest")).toBe(digest);
  expect(request.body.get("expected_installed_version")).toBe("1.2.0");
});

it("preserves explicit version confirmation for URL updates and keeps it false by default", async () => {
  const fetch = vi
    .fn()
    .mockImplementation(
      async () => new Response(JSON.stringify({ status: "active" })),
    );
  vi.stubGlobal("fetch", fetch);
  await updatePluginFromUrl(
    "example.update",
    "https://packages.example/preview.upt",
    confirmation,
    digest,
    true,
  );
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toMatchObject({
    version_change_confirmed: true,
    expected_installed_version: "1.2.0",
    expected_digest: digest,
  });
  await updatePluginFromUrl(
    "example.update",
    "https://packages.example/preview.upt",
    { approvedPermissions: [] },
    digest,
  );
  expect(JSON.parse(fetch.mock.calls[1][1].body).version_change_confirmed).toBe(
    false,
  );
});

it("preserves a safe activation failure message for the active review dialog", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail:
            "The installed plugin changed after review. Review the package again.",
        }),
        { status: 409 },
      ),
    ),
  );
  await expect(
    updatePlugin(
      "example.update",
      new File(["package"], "preview.upt"),
      confirmation,
    ),
  ).rejects.toThrow("changed after review");
});
