import { beforeEach, expect, it, vi } from "vitest";
import { fetchCurrentUser } from "../services/auth";
import {
  authChecked,
  authCheckFailed,
  checkAuth,
  currentUser,
  ensureAuthChecked,
} from "../state/auth";
vi.mock("../services/auth", () => ({ fetchCurrentUser: vi.fn() }));
const user = {
  id: "signed-in",
  username: "member",
  email: "member@example.invalid",
  is_admin: false,
  steamgriddb_api_key: null,
};
beforeEach(() => {
  vi.mocked(fetchCurrentUser).mockReset();
  currentUser.value = null;
  authChecked.value = false;
  authCheckFailed.value = false;
});
it("retries an unavailable startup authentication check on the next navigation", async () => {
  vi.mocked(fetchCurrentUser)
    .mockRejectedValueOnce(new Error("starting"))
    .mockResolvedValueOnce(user);
  await ensureAuthChecked();
  expect(authChecked.value).toBe(true);
  expect(authCheckFailed.value).toBe(true);
  await ensureAuthChecked();
  expect(currentUser.value).toEqual(user);
  expect(authCheckFailed.value).toBe(false);
});
it("an earlier anonymous response cannot overwrite a later signed-in check", async () => {
  let finish!: (value: null) => void;
  vi.mocked(fetchCurrentUser)
    .mockReturnValueOnce(
      new Promise((resolve) => {
        finish = resolve;
      }),
    )
    .mockResolvedValueOnce(user);
  const earlier = checkAuth();
  await checkAuth();
  finish(null);
  await earlier;
  expect(currentUser.value).toEqual(user);
  expect(authCheckFailed.value).toBe(false);
});
it("a confirmed anonymous check is reused without extra requests", async () => {
  vi.mocked(fetchCurrentUser).mockResolvedValue(null);
  await ensureAuthChecked();
  await ensureAuthChecked();
  expect(fetchCurrentUser).toHaveBeenCalledTimes(1);
  expect(authCheckFailed.value).toBe(false);
});
