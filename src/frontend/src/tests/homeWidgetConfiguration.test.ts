import { expect, it } from "vitest";
import { widgetConfiguration } from "../services/homeWidgets";
import type { UiField } from "../services/pluginUi";

const fields: UiField[] = [
  {
    id: "limit",
    label: "Items",
    description: "",
    type: "number",
    required: true,
    secret: false,
    options: [],
    default: 3,
    validation: { minimum: 1, maximum: 8 },
  },
  {
    id: "compact",
    label: "Compact",
    description: "",
    type: "boolean",
    required: false,
    secret: false,
    options: [],
    default: false,
  },
];

it("uses validated saved personal options and discards undeclared fields", () => {
  expect(
    widgetConfiguration(fields, { limit: 5, compact: true, undeclared: "old" }),
  ).toEqual({ limit: 5, compact: true });
});
it.each([0, 9, Infinity, "4"])(
  "restores the declared default for invalid saved values (%s)",
  (limit) => {
    expect(widgetConfiguration(fields, { limit })).toEqual({
      limit: 3,
      compact: false,
    });
  },
);
it("never forwards a secret from personal widget preferences", () => {
  expect(
    widgetConfiguration([{ ...fields[0]!, type: "password", secret: true }], {
      limit: "token",
    }),
  ).toEqual({});
});
it("treats a schema null default as an absent optional value", () => {
  expect(
    widgetConfiguration([{ ...fields[0]!, required: false, default: null }]),
  ).toEqual({});
});
