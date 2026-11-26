import { describe, expect, it } from "vitest";
import { searchSettings } from "../utils/settingsSearch";

const places = (query: string, admin = false) =>
  searchSettings(query, admin).map((e) => `${e.section}:${e.tab}`);
const labels = (query: string, admin = false) =>
  searchSettings(query, admin).map((e) => e.label);

describe("searchSettings", () => {
  it("finds nothing for an empty search", () => {
    expect(places("")).toEqual([]);
    expect(places("   ")).toEqual([]);
  });

  it("puts a setting whose name starts with the word first", () => {
    expect(labels("compact")[0]).toBe("Compact mode");
    expect(labels("episode aired")[0]).toBe("Episode aired");
  });

  it("finds a setting by what it does and opens its tab", () => {
    expect(places("wishlist")).toContain("sources:saved");
    expect(places("tmdb")).toContain("sources:providers");
    expect(places("csv")).toContain("library:io");
    expect(places("ribbon")).toContain("look:appearance");
  });

  it("needs every word to match", () => {
    expect(places("steam wishlist")).toContain("sources:saved");
    expect(places("steam zzzz")).toEqual([]);
  });

  it("is not thrown by case or punctuation", () => {
    expect(places("IMPORT / export")).toContain("library:io");
  });

  it("keeps admin settings to admins", () => {
    expect(places("sso")).toEqual([]);
    expect(places("sso", true)).toContain("server:access");
  });

  it("shows where each result lives", () => {
    const [first] = searchSettings("compact", false);
    expect(first.where).toBe("Look and feel, Library views");
  });
});
