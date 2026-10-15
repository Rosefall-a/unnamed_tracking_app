import { describe, expect, it } from "vitest";
import { searchSettings } from "../utils/settingsSearch";

const ids = (query: string, admin = false) =>
  searchSettings(query, admin).map((e) => e.id);

describe("searchSettings", () => {
  it("finds nothing for an empty search", () => {
    expect(ids("")).toEqual([]);
    expect(ids("   ")).toEqual([]);
  });

  it("puts a page whose name starts with the word first", () => {
    expect(ids("appear")[0]).toBe("appearance");
    expect(ids("noti")[0]).toBe("notifications");
  });

  it("finds a page by what is on it", () => {
    expect(ids("wishlist")).toContain("scan");
    expect(ids("tmdb")).toContain("sources");
    expect(ids("backup")).toContain("export");
  });

  it("needs every word to match", () => {
    expect(ids("steam wishlist")).toContain("scan");
    expect(ids("steam zzzz")).toEqual([]);
  });

  it("is not thrown by case or punctuation", () => {
    expect(ids("EXPORT / import")).toContain("export");
  });

  it("keeps admin pages to admins", () => {
    expect(ids("sso")).toEqual([]);
    expect(ids("sso", true)).toContain("oidc");
  });
});
