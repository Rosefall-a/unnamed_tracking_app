import { describe, expect, it } from "vitest";
import {
  SETTINGS_PAGES,
  resolveSettingsPlace,
  visiblePages,
} from "../utils/settingsPages";

const at = (section?: string, tab?: string, admin = false) =>
  resolveSettingsPlace(section, tab, admin);

describe("settings pages", () => {
  it("opens a page on its first tab when no tab is given", () => {
    expect(at("look")).toEqual({ section: "look", tab: "appearance" });
  });

  it("falls back to Account, Profile for anything unknown", () => {
    expect(at(undefined)).toEqual({ section: "account", tab: "profile" });
    expect(at("nope")).toEqual({ section: "account", tab: "profile" });
  });

  it("sends old section links to their new page and tab", () => {
    expect(at("interface")).toEqual({ section: "look", tab: "views" });
    expect(at("upload")).toEqual({ section: "library", tab: "upload" });
    expect(at("media-trash")).toEqual({ section: "library", tab: "trash" });
    expect(at("sources")).toEqual({ section: "sources", tab: "providers" });
    expect(at("stats")).toEqual({ section: "server", tab: "overview" });
  });

  it("sends old page plus tab links to the new place", () => {
    expect(at("library", "preferences")).toEqual({
      section: "look",
      tab: "views",
    });
    expect(at("metadata", "scan")).toEqual({
      section: "sources",
      tab: "saved",
    });
    expect(at("admin", "sso", true)).toEqual({
      section: "server",
      tab: "access",
    });
  });

  it("keeps admin tabs from everyone else", () => {
    expect(at("server", "users")).toEqual({
      section: "server",
      tab: "overview",
    });
    expect(at("admin", "backups")).toEqual({
      section: "server",
      tab: "overview",
    });
    expect(at("server", "users", true)).toEqual({
      section: "server",
      tab: "users",
    });
    const nonAdminServer = visiblePages(false).find((p) => p.id === "server");
    expect(nonAdminServer).toBeTruthy();
  });

  it("puts every section on exactly one tab", () => {
    const parts = SETTINGS_PAGES.flatMap((p) => p.tabs.flatMap((t) => t.parts));
    expect(new Set(parts).size).toBe(parts.length);
  });
});
