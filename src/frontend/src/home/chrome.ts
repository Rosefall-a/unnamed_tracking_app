// The look options every widget shares (heading, background, card size). They
// are stored in the widget's settings under names that start with an underscore
// so they never clash with a widget's own settings, and handed down to the
// frame and the card rows without each widget passing them along.
import type { ComputedRef, InjectionKey } from "vue";

export type PanelMode = "auto" | "panel" | "plain";
export type CardSize = "small" | "medium" | "large";
export type CardText = "always" | "hover" | "never";
// when a card says what kind of title it is: only on rows that mix kinds
export type CardTag = "auto" | "always" | "never";

export interface Chrome {
  heading: string;
  showHeading: boolean;
  panel: PanelMode;
  cardSize: CardSize;
  cardText: CardText;
  cardTag: CardTag;
}

export const CHROME_KEY: InjectionKey<ComputedRef<Chrome>> =
  Symbol("widget-chrome");

export const CHROME_DEFAULTS: Record<string, unknown> = {
  _heading: "",
  _showHeading: true,
  _panel: "auto",
  _cardSize: "medium",
  _cardText: "always",
  _cardTag: "auto",
};

function pick<T extends string>(value: unknown, allowed: T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}

export function chromeFrom(settings: Record<string, unknown>): Chrome {
  return {
    heading: typeof settings._heading === "string" ? settings._heading : "",
    showHeading: settings._showHeading !== false,
    panel: pick(settings._panel, ["auto", "panel", "plain"], "auto"),
    cardSize: pick(settings._cardSize, ["small", "medium", "large"], "medium"),
    cardText: pick(settings._cardText, ["always", "hover", "never"], "always"),
    cardTag: pick(settings._cardTag, ["auto", "always", "never"], "auto"),
  };
}
