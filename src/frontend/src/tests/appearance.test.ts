import { afterEach, expect, it, vi } from "vitest";
import { currentUser } from "../state/auth";
import {
  appearanceSettings,
  appearanceLoaded,
  loadAppearanceSettings,
  resetAppearanceSettings,
} from "../state/appearance";

const user = (id: string) => ({
  id,
  username: id,
  email: `${id}@example.invalid`,
  is_admin: false,
  steamgriddb_api_key: null,
});
afterEach(() => {
  resetAppearanceSettings();
  currentUser.value = null;
  vi.unstubAllGlobals();
});

it("clears personal badges and ignores responses from the previous account", async () => {
  let complete!: (response: Response) => void;
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<Response>((resolve) => {
            complete = resolve;
          }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            user_id: "second",
            completion_badge_style: "ribbon",
          }),
        ),
      ),
  );
  currentUser.value = user("first");
  const first = loadAppearanceSettings();
  currentUser.value = user("second");
  expect(appearanceSettings.value).toBeNull();
  expect(appearanceLoaded.value).toBe(false);
  await loadAppearanceSettings();
  complete(
    new Response(
      JSON.stringify({ user_id: "first", completion_badge_style: "glow" }),
    ),
  );
  await first;
  expect(appearanceSettings.value).toMatchObject({
    user_id: "second",
    completion_badge_style: "ribbon",
  });
});
