import { describe, expect, it } from "vitest";
import {
  CORE_SHORTCUTS,
  type ShortcutDefinition,
} from "../utils/shortcutDefinitions";
import {
  prepareShortcutOverride,
  reconcileShortcutOverrides,
  resolveShortcuts,
} from "../utils/shortcutResolution";

const plugin: ShortcutDefinition = {
  id: "plugin:example.shortcuts:conflict",
  pluginId: "example.shortcuts",
  label: "Example conflict",
  group: "Example",
  keys: ["Ctrl+K"],
};
const definitions = [...CORE_SHORTCUTS, plugin];
const binding = (
  overrides: Parameters<typeof resolveShortcuts>[1],
  id: string,
) => resolveShortcuts(definitions, overrides).find((item) => item.id === id)!;

describe("oldest enabled shortcut ownership", () => {
  it("disables a new conflict, lets it take released keys, and blocks re-enabled core keys across reload", () => {
    let result = reconcileShortcutOverrides(definitions, {});
    expect(result.disabled.map((item) => item.id)).toEqual([plugin.id]);
    expect(result.overrides[plugin.id].enabled).toBe(false);
    const firstOrder = result.overrides[plugin.id].enabled_order!;
    result = prepareShortcutOverride(
      definitions,
      result.overrides,
      "app.search",
      { enabled: false },
    );
    result = prepareShortcutOverride(definitions, result.overrides, plugin.id, {
      enabled: true,
    });
    expect(binding(result.overrides, plugin.id).activeKeys).toEqual(["Ctrl+K"]);
    expect(result.overrides[plugin.id].enabled_order).toBeGreaterThan(
      firstOrder,
    );
    result = prepareShortcutOverride(
      definitions,
      result.overrides,
      "app.search",
      { enabled: true },
    );
    expect(result.disabled.map((item) => item.id)).toEqual(["app.search"]);
    expect(result.overrides["app.search"].enabled).toBe(false);
    const reloaded = reconcileShortcutOverrides(
      definitions,
      JSON.parse(JSON.stringify(result.overrides)),
    );
    expect(binding(reloaded.overrides, plugin.id).enabled).toBe(true);
    expect(binding(reloaded.overrides, "app.search").conflicts[0].id).toBe(
      plugin.id,
    );
    expect(reloaded.disabled).toEqual([]);
  });

  it("keeps blocked bindings off when their owner disappears and preserves plugin priority on reinstall", () => {
    let result = reconcileShortcutOverrides(definitions, {});
    result = prepareShortcutOverride(
      definitions,
      result.overrides,
      "app.search",
      { enabled: false },
    );
    result = prepareShortcutOverride(definitions, result.overrides, plugin.id, {
      enabled: true,
    });
    result = prepareShortcutOverride(
      definitions,
      result.overrides,
      "app.search",
      { enabled: true },
    );
    const without = reconcileShortcutOverrides(
      CORE_SHORTCUTS,
      result.overrides,
    );
    expect(resolveShortcuts(CORE_SHORTCUTS, without.overrides)[0].enabled).toBe(
      false,
    );
    const reinstalled = reconcileShortcutOverrides(
      definitions,
      without.overrides,
    );
    expect(binding(reinstalled.overrides, plugin.id).enabled).toBe(true);
    expect(reinstalled.disabled).toEqual([]);
  });

  it("treats remapping an active binding as a new claim, without stealing older keys", () => {
    const unique = { ...plugin, keys: ["Alt+Shift+Q"] };
    const defs = [...CORE_SHORTCUTS, unique];
    const initial = reconcileShortcutOverrides(defs, {});
    const remapped = prepareShortcutOverride(
      defs,
      initial.overrides,
      "app.search",
      { keys: unique.keys },
    );
    expect(remapped.overrides["app.search"].enabled).toBe(false);
    expect(remapped.disabled[0].conflicts[0].id).toBe(plugin.id);
    const repaired = prepareShortcutOverride(
      defs,
      remapped.overrides,
      "app.search",
      { enabled: true, keys: ["CtrlOrMeta+L"] },
    );
    expect(resolveShortcuts(defs, repaired.overrides)[0].activeKeys).toEqual([
      "CtrlOrMeta+L",
    ]);
    expect(repaired.disabled).toEqual([]);
  });

  it("disables a whole conflicting binding rather than leaving invisible alternatives active", () => {
    const alternate = { ...plugin, keys: ["Ctrl+K", "Alt+Shift+Q"] };
    const result = reconcileShortcutOverrides(
      [...CORE_SHORTCUTS, alternate],
      {},
    );
    const resolved = resolveShortcuts(
      [...CORE_SHORTCUTS, alternate],
      result.overrides,
    ).at(-1)!;
    expect(resolved.enabled).toBe(false);
    expect(resolved.activeKeys).toEqual([]);
    expect(resolved.keys).toHaveLength(2);
  });

  it("allows the same key in separate page scopes and compacts imported orders safely", () => {
    const local = {
      ...plugin,
      keys: ["J"],
      paths: ["/plugins/example.shortcuts/home"],
    };
    const result = reconcileShortcutOverrides([...CORE_SHORTCUTS, local], {
      "app.search": { enabled_order: Number.MAX_SAFE_INTEGER },
    });
    expect(result.disabled).toEqual([]);
    expect(
      Object.values(result.overrides).every((item) =>
        Number.isSafeInteger(item.enabled_order),
      ),
    ).toBe(true);
    expect(result.overrides[local.id].enabled_order).toBeLessThan(1000);
  });
});
