import type { RouteLocationRaw } from "vue-router";
import type { PluginNavigationContribution } from "../state/pluginExtensions";

export function pluginNavigationTarget(
  item: PluginNavigationContribution,
): RouteLocationRaw {
  if (item.settingsSectionId)
    return {
      path: "/settings",
      query: { section: item.settingsSectionId, area: item.area },
    };
  return {
    name: "plugin-route",
    params: {
      pluginId: item.pluginId,
      pluginPath: item.routePath || item.pageId,
    },
  };
}
