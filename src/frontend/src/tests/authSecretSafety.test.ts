import { afterEach, describe, expect, it, vi } from "vitest";

import { login, updateProfile } from "../services/auth";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("authentication secret safety", () => {
  it("keeps login credentials out of the request URL", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await login("person@example.com", "SuperSecret123!");

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/auth/login");
    expect(url).not.toContain("SuperSecret123!");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(String(init.body))).toEqual({
      username_or_email: "person@example.com",
      password: "SuperSecret123!",
    });
  });

  it("does not display a reflected login password from an error response", async () => {
    const secret = "SuperSecret123!";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: `Rejected ${secret}` }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(login("person@example.com", secret)).rejects.toThrow(
      "Login failed",
    );
    await expect(login("person@example.com", secret)).rejects.not.toThrow(
      secret,
    );
  });

  it("does not display reflected profile passwords from an error response", async () => {
    const secret = "CurrentSecret123!";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: `Rejected ${secret}` }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(
      updateProfile({ currentPassword: secret, newPassword: "NewSecret123!" }),
    ).rejects.toThrow("Failed to update profile");
  });
});
