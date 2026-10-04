import {
  parseDeviceAppearance,
  type DeviceAppearance,
} from "./deviceAppearance";
import type { UiAppearance } from "../state/uiAppearance";

// Cosmetic values only: never store identity, onboarding state or application data.
export const UI_PREFERENCES_COOKIE = "uta-ui-preferences";
export interface CachedUiPreferences extends DeviceAppearance {
  density: UiAppearance["ui_density"];
  style: UiAppearance["ui_style"];
  reduceMotion: boolean;
}

export function readUiPreferencesCookie(): CachedUiPreferences | null {
  try {
    const entry = document.cookie
      .split(";")
      .map((part) => part.trim())
      .find((part) => part.startsWith(`${UI_PREFERENCES_COOKIE}=`));
    if (!entry || entry.length > 4096) return null;
    const raw = decodeURIComponent(
      entry.slice(UI_PREFERENCES_COOKIE.length + 1),
    );
    const appearance = parseDeviceAppearance(raw);
    const value = JSON.parse(raw);
    if (
      !appearance ||
      !["comfortable", "compact"].includes(value.density) ||
      value.style !== "archive-pocket" ||
      typeof value.reduceMotion !== "boolean"
    )
      return null;
    return {
      ...appearance,
      density: value.density,
      style: value.style,
      reduceMotion: value.reduceMotion,
    };
  } catch {
    return null;
  }
}

export function saveUiPreferencesCookie(
  device: DeviceAppearance,
  value: UiAppearance,
): void {
  const cache: CachedUiPreferences = {
    ...device,
    density: value.ui_density,
    style: value.ui_style,
    reduceMotion: value.ui_reduce_motion,
  };
  try {
    const encoded = encodeURIComponent(JSON.stringify(cache));
    if (encoded.length + UI_PREFERENCES_COOKIE.length > 4000) return;
    const secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `${UI_PREFERENCES_COOKIE}=${encoded}; Path=/; Max-Age=31536000; SameSite=Lax${secure}`;
  } catch {
    // Cookie restrictions do not prevent account preferences from working.
  }
}
