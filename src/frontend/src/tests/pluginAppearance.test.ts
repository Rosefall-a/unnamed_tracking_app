import { afterEach, expect, it, vi } from "vitest";
import {
  observePluginAppearance,
  readPluginAppearance,
} from "../services/pluginAppearance";
afterEach(() => vi.unstubAllGlobals());
it("exposes only public cosmetic tokens and releases its observer", () => {
  const classes = new Set(["high-contrast"]);
  const root = {
    dataset: { theme: "dark" },
    classList: { contains: (key: string) => classes.has(key) },
  };
  vi.stubGlobal("document", { documentElement: root });
  vi.stubGlobal("getComputedStyle", () => ({
    getPropertyValue: (name: string) => (name === "--ui-bg" ? "#123456" : ""),
  }));
  let changed = () => {};
  const disconnect = vi.fn();
  vi.stubGlobal(
    "MutationObserver",
    class {
      constructor(callback: () => void) {
        changed = callback;
      }
      observe = vi.fn();
      disconnect = disconnect;
    },
  );
  const initial = readPluginAppearance();
  expect(initial).toMatchObject({
    api_contract_version: "1.1.0",
    mode: "dark",
    high_contrast: true,
    tokens: { "--ui-bg": "#123456" },
  });
  expect(Object.keys(initial)).toEqual([
    "api_contract_version",
    "mode",
    "high_contrast",
    "reduce_motion",
    "navigation_shortcuts",
    "global_shortcuts",
    "keyboard_shortcuts",
    "tokens",
  ]);
  expect(
    Object.keys(initial.tokens).every((key) => key.startsWith("--ui-")),
  ).toBe(true);
  const callback = vi.fn();
  const stop = observePluginAppearance(callback);
  expect(callback).toHaveBeenCalledTimes(1);
  root.dataset.theme = "light";
  changed();
  expect(callback.mock.lastCall?.[0].mode).toBe("light");
  stop();
  expect(disconnect).toHaveBeenCalledOnce();
});
