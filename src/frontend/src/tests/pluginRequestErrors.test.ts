import { afterEach, describe, expect, it, vi } from "vitest";
import {
  enablePlugin,
  installPlugin,
  previewPluginUpdate,
  previewPluginUpdateUrl,
  updatePlugin,
} from "../services/plugins";
import { dispatchPluginAction } from "../services/pluginUi";

afterEach(() => vi.unstubAllGlobals());
const confirmation = { approvedPermissions: [] };
const file = new File(["package"], "review.utp");

describe("plugin compatibility rejection details", () => {
  it.each([
    ["enable", () => enablePlugin("example")],
    ["upload update preview", () => previewPluginUpdate("example", file)],
    [
      "URL update preview",
      () =>
        previewPluginUpdateUrl("example", "https://example.invalid/plugin.utp"),
    ],
    ["upload update", () => updatePlugin("example", file, confirmation)],
    ["upload installation", () => installPlugin(file, confirmation)],
    ["plugin action", () => dispatchPluginAction("example", "get-config")],
  ])(
    "preserves the server's version explanation for %s",
    async (_name, run) => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(
          new Response(
            JSON.stringify({
              detail: {
                code: "incompatible",
                message:
                  "Host SDK 1.1.0 does not satisfy ^2.0.0; choose a compatible release.",
              },
            }),
            { status: 409 },
          ),
        ),
      );
      await expect(run()).rejects.toThrow(
        "Host SDK 1.1.0 does not satisfy ^2.0.0",
      );
    },
  );
  it("keeps string details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail:
              "Whole plugin stopped until a verified v1.1 update is installed.",
          }),
          { status: 400 },
        ),
      ),
    );
    await expect(enablePlugin("example")).rejects.toThrow(
      "Whole plugin stopped",
    );
  });
  it("handles malformed and validation error responses without dumping request input", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(new Response("not JSON", { status: 502 }))
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              detail: [
                { msg: "version range is invalid", input: "do not disclose" },
              ],
            }),
            { status: 422 },
          ),
        ),
    );
    await expect(enablePlugin("example")).rejects.toThrow("(502)");
    await expect(enablePlugin("example")).rejects.toThrow(
      "version range is invalid",
    );
  });
  it("keeps the action status and the missing capability explanation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail:
              "The plugin needs plugin.storage approval. Review its access in Plugin Manager.",
          }),
          { status: 403 },
        ),
      ),
    );
    await expect(
      dispatchPluginAction("example", "get-config"),
    ).rejects.toMatchObject({
      status: 403,
      message: expect.stringContaining("plugin.storage approval"),
    });
  });
});
