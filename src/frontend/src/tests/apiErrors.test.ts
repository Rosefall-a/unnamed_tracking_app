import { describe, expect, it } from "vitest";
import { apiError } from "../services/apiErrors";

describe("apiError", () => {
  it("uses a useful detail message without appending the raw response body", async () => {
    const secret = "super-secret-password";
    const response = new Response(
      JSON.stringify({ detail: "Invalid credentials.", password: secret }),
      { status: 401, headers: { "Content-Type": "application/json" } },
    );

    const error = await apiError(response, "Request failed");

    expect(error.message).toBe("Invalid credentials.");
    expect(error.message).not.toContain(secret);
  });

  it("reduces validation details to their messages", async () => {
    const secret = "another-secret-token";
    const response = new Response(
      JSON.stringify({
        detail: [
          { type: "value_error", loc: ["body", "token"], msg: "Token is invalid.", input: secret },
          { type: "value_error", loc: ["body", "password"], msg: "Password is invalid.", input: "plain-text-password" },
        ],
      }),
      { status: 422, headers: { "Content-Type": "application/json" } },
    );

    const error = await apiError(response, "Request failed");

    expect(error.message).toBe("Token is invalid. Password is invalid.");
    expect(error.message).not.toContain(secret);
    expect(error.message).not.toContain("plain-text-password");
  });

  it("falls back without reading or exposing non-JSON response bodies", async () => {
    const secret = "server-stack-trace-secret";
    const response = new Response(secret, { status: 500 });

    const error = await apiError(response, "Request failed");

    expect(error.message).toBe("Request failed (500)");
    expect(error.message).not.toContain(secret);
  });
});
