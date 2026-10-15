// What a widget on the Home page can do to itself without the edit mode: change
// its own settings from controls on the widget, which are saved as you go.
import type { ComputedRef, InjectionKey } from "vue";
import type { WidgetDefinition } from "./registry";

export interface WidgetContext {
  id: string;
  def: WidgetDefinition;
  // the settings it runs with, defaults included
  settings: Record<string, unknown>;
  variant: string | null;
  w: number;
  h: number;
  update(changes: Record<string, unknown>): void;
  setVariant(variant: string): void;
}

export const WIDGET_CONTEXT: InjectionKey<ComputedRef<WidgetContext | null>> =
  Symbol("widget-context");

// provided by the Home page, which owns the layout
export type UpdateWidget = (
  id: string,
  settings: Record<string, unknown>,
  variant: string | null,
) => void;
export const UPDATE_WIDGET: InjectionKey<UpdateWidget> =
  Symbol("update-widget");
